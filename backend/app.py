import os
from datetime import datetime, date

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from models import init_db, get_db, get_or_create_user
from telegram_auth import validate_init_data

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
# Set to "true" only while testing locally without a real Telegram session
SKIP_AUTH_CHECK = os.environ.get("SKIP_AUTH_CHECK", "false").lower() == "true"

app = Flask(__name__)
CORS(app)
init_db()


def authed_user():
    """
    Pulls the Telegram user out of the request's initData (sent as a header),
    verifies it against the bot token, and returns the matching DB row.
    Returns None if auth fails.
    """
    init_data = request.headers.get("X-Telegram-Init-Data", "")

    if SKIP_AUTH_CHECK:
        # Local dev fallback: trust a plain telegram_id in the body/query instead
        tg_id = request.headers.get("X-Debug-Telegram-Id") or request.args.get("telegram_id")
        if not tg_id:
            return None
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    tg_user = validate_init_data(init_data, BOT_TOKEN)
    if not tg_user:
        return None

    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_user["id"],)).fetchone()
    conn.close()
    return dict(row) if row else None


@app.post("/api/auth")
def auth():
    """
    Called once when the Mini App loads. Verifies initData, creates the user
    on first visit (crediting the referrer if a start_param / ref code was
    passed through the bot's deep link), and returns their profile.
    """
    init_data = request.headers.get("X-Telegram-Init-Data", "")

    if SKIP_AUTH_CHECK:
        body = request.get_json(force=True, silent=True) or {}
        tg_user = {
            "id": body.get("telegram_id"),
            "username": body.get("username", "dev_user"),
            "first_name": body.get("first_name", "Dev"),
            "_start_param": body.get("ref"),
        }
        if not tg_user["id"]:
            return jsonify(error="telegram_id required in SKIP_AUTH_CHECK mode"), 400
    else:
        tg_user = validate_init_data(init_data, BOT_TOKEN)
        if not tg_user:
            return jsonify(error="invalid or expired Telegram session"), 401

    user = get_or_create_user(
        telegram_id=tg_user["id"],
        username=tg_user.get("username", ""),
        first_name=tg_user.get("first_name", ""),
        referred_by_code=tg_user.get("_start_param"),
    )
    return jsonify(user=user)


@app.get("/api/state")
def state():
    """Everything the Home/Earn screens need in one call."""
    user = authed_user()
    if not user:
        return jsonify(error="unauthorized"), 401

    conn = get_db()
    tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE is_active = 1").fetchall()]
    banners = [dict(r) for r in conn.execute(
        "SELECT * FROM banners WHERE is_active = 1 ORDER BY sort_order, id DESC"
    ).fetchall()]
    watched_banner_ids = [r["banner_id"] for r in conn.execute(
        "SELECT banner_id FROM banner_views WHERE user_id = ?", (user["id"],)
    ).fetchall()]
    referral_count = conn.execute(
        "SELECT COUNT(*) c FROM users WHERE referred_by = ?", (user["id"],)
    ).fetchone()["c"]
    referral_earned = conn.execute(
        "SELECT COALESCE(SUM(bonus), 0) s FROM referral_bonuses WHERE referrer_id = ?", (user["id"],)
    ).fetchone()["s"]
    recent_signups = conn.execute(
        "SELECT username, first_name, created_at FROM users WHERE referred_by = ? "
        "ORDER BY created_at DESC LIMIT 10",
        (user["id"],),
    ).fetchall()
    conn.close()

    today = date.today().isoformat()
    claimed_today = user["last_daily_claim"] == today

    return jsonify(
        user=user,
        tasks=tasks,
        banners=banners,
        watched_banner_ids=watched_banner_ids,
        daily=dict(streak=user["daily_streak"], claimed_today=claimed_today),
        referrals=dict(
            count=referral_count,
            earned=referral_earned,
            code=user["referral_code"],
        ),
        recent_signups=[dict(r) for r in recent_signups],
        # These two are UI placeholders, not real records -- swap or remove
        # once you decide whether "social proof" content should exist at all.
        sample_disclaimer="feed/leaderboard below are placeholder UI content, not live user data",
    )


@app.post("/api/tasks/<int:task_id>/complete")
def complete_task(task_id):
    user = authed_user()
    if not user:
        return jsonify(error="unauthorized"), 401

    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ? AND is_active = 1", (task_id,)).fetchone()
    if not task:
        conn.close()
        return jsonify(error="task not found"), 404

    # Reward is queued for review, NOT auto-credited to balance.
    # Wire this up to whatever actually verifies the task was done
    # (e.g. a webhook from the ad network / survey partner) before paying out.
    reward = task["reward_min"]
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO task_completions (user_id, task_id, reward, status, created_at) VALUES (?,?,?,?,?)",
        (user["id"], task_id, reward, "pending_review", now),
    )
    conn.commit()
    conn.close()
    return jsonify(status="submitted_for_review", reward=reward)


@app.post("/api/rewards/daily/claim")
def claim_daily():
    user = authed_user()
    if not user:
        return jsonify(error="unauthorized"), 401

    today = date.today().isoformat()
    if user["last_daily_claim"] == today:
        return jsonify(error="already claimed today"), 400

    new_streak = user["daily_streak"] + 1 if user["daily_streak"] < 7 else 1
    reward = round(0.5 * new_streak, 2)

    conn = get_db()
    conn.execute(
        "UPDATE users SET daily_streak = ?, last_daily_claim = ?, balance = balance + ? WHERE id = ?",
        (new_streak, today, reward, user["id"]),
    )
    conn.commit()
    conn.close()
    return jsonify(streak=new_streak, reward=reward)


@app.post("/api/withdraw")
def withdraw():
    user = authed_user()
    if not user:
        return jsonify(error="unauthorized"), 401

    body = request.get_json(force=True, silent=True) or {}
    amount = body.get("amount")
    method = body.get("method")
    account = body.get("account")

    if not all([amount, method, account]):
        return jsonify(error="amount, method and account are required"), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify(error="invalid amount"), 400

    if amount < 10:
        return jsonify(error="minimum withdrawal is $10.00"), 400
    if amount > user["balance"]:
        return jsonify(error="amount exceeds available balance"), 400

    conn = get_db()
    now = datetime.utcnow().isoformat()
    # Status starts at 'pending' -- always requires manual/admin approval
    # before money moves and before the balance is deducted.
    conn.execute(
        "INSERT INTO withdrawals (user_id, amount, method, account, status, created_at) VALUES (?,?,?,?,?,?)",
        (user["id"], amount, method, account, "pending", now),
    )
    conn.commit()
    conn.close()
    return jsonify(status="pending", message="Withdrawal request submitted for review")


@app.post("/api/privacy/accept")
def accept_privacy():
    user = authed_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    conn = get_db()
    conn.execute(
        "UPDATE users SET privacy_accepted_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), user["id"]),
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "")


@app.post("/api/internal/set-phone")
def set_phone():
    """
    Called by the BOT (not the browser) once it receives a verified contact
    share from Telegram. Protected by a shared secret instead of initData,
    since this call originates from your own server, not a user's session.
    """
    if not INTERNAL_SECRET or request.headers.get("X-Internal-Secret") != INTERNAL_SECRET:
        return jsonify(error="unauthorized"), 401

    body = request.get_json(force=True, silent=True) or {}
    telegram_id = body.get("telegram_id")
    phone = body.get("phone")
    if not telegram_id or not phone:
        return jsonify(error="telegram_id and phone are required"), 400

    conn = get_db()
    conn.execute(
        "UPDATE users SET phone = ?, phone_verified_at = ? WHERE telegram_id = ?",
        (phone, datetime.utcnow().isoformat(), telegram_id),
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")


def admin_ok():
    return ADMIN_SECRET and request.headers.get("X-Admin-Secret") == ADMIN_SECRET


@app.get("/api/admin/tasks")
def admin_list_tasks():
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify(tasks=rows)


@app.post("/api/admin/tasks")
def admin_create_task():
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    b = request.get_json(force=True, silent=True) or {}
    required = ["title", "description", "category", "reward_min", "reward_max"]
    if not all(b.get(k) not in (None, "") for k in required):
        return jsonify(error=f"required fields: {', '.join(required)}"), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO tasks (title, description, category, tag, reward_min, reward_max, is_active) "
        "VALUES (?,?,?,?,?,?,1)",
        (b["title"], b["description"], b["category"], b.get("tag", ""), float(b["reward_min"]), float(b["reward_max"])),
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@app.put("/api/admin/tasks/<int:task_id>")
def admin_update_task(task_id):
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    b = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET title=?, description=?, category=?, tag=?, reward_min=?, reward_max=?, is_active=? "
        "WHERE id=?",
        (b["title"], b["description"], b["category"], b.get("tag", ""),
         float(b["reward_min"]), float(b["reward_max"]), int(bool(b.get("is_active", True))), task_id),
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@app.delete("/api/admin/tasks/<int:task_id>")
def admin_delete_task(task_id):
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@app.get("/api/admin/banners")
def admin_list_banners():
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM banners ORDER BY sort_order, id DESC").fetchall()]
    conn.close()
    return jsonify(banners=rows)


@app.post("/api/admin/banners")
def admin_create_banner():
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    b = request.get_json(force=True, silent=True) or {}
    if not b.get("title"):
        return jsonify(error="title is required"), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO banners (title, description, image_url, link_url, media_type, points, sort_order, is_active, created_at) "
        "VALUES (?,?,?,?,?,?,?,1,?)",
        (b["title"], b.get("description", ""), b.get("image_url", ""), b.get("link_url", ""),
         b.get("media_type", "link"), int(b.get("points", 0)), int(b.get("sort_order", 0)), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@app.put("/api/admin/banners/<int:banner_id>")
def admin_update_banner(banner_id):
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    b = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    conn.execute(
        "UPDATE banners SET title=?, description=?, image_url=?, link_url=?, media_type=?, points=?, sort_order=?, is_active=? WHERE id=?",
        (b["title"], b.get("description", ""), b.get("image_url", ""), b.get("link_url", ""),
         b.get("media_type", "link"), int(b.get("points", 0)), int(b.get("sort_order", 0)),
         int(bool(b.get("is_active", True))), banner_id),
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@app.delete("/api/admin/banners/<int:banner_id>")
def admin_delete_banner(banner_id):
    if not admin_ok():
        return jsonify(error="unauthorized"), 401
    conn = get_db()
    conn.execute("DELETE FROM banners WHERE id = ?", (banner_id,))
    conn.commit()
    conn.close()
    return jsonify(status="ok")


ALL_TUTORIALS_BONUS_POINTS = 50


@app.post("/api/banners/<int:banner_id>/watch")
def watch_banner(banner_id):
    """
    Called once when a user opens a 'video' banner fullscreen. Awards points
    exactly once per user per video (enforced by a UNIQUE constraint, not
    just app logic, so this can't be farmed by spamming the endpoint).
    """
    user = authed_user()
    if not user:
        return jsonify(error="unauthorized"), 401

    conn = get_db()
    banner = conn.execute("SELECT * FROM banners WHERE id = ? AND is_active = 1", (banner_id,)).fetchone()
    if not banner:
        conn.close()
        return jsonify(error="not found"), 404

    already = conn.execute(
        "SELECT 1 FROM banner_views WHERE user_id = ? AND banner_id = ?", (user["id"], banner_id)
    ).fetchone()

    newly_awarded = 0
    bonus_awarded = 0
    if not already:
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO banner_views (user_id, banner_id, points, created_at) VALUES (?,?,?,?)",
            (user["id"], banner_id, banner["points"], now),
        )
        conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (banner["points"], user["id"]))
        newly_awarded = banner["points"]
        conn.commit()

        # Check if this completes the full tutorial set
        total_videos = conn.execute(
            "SELECT COUNT(*) c FROM banners WHERE media_type = 'video' AND is_active = 1"
        ).fetchone()["c"]
        watched_videos = conn.execute(
            "SELECT COUNT(*) c FROM banner_views bv JOIN banners b ON b.id = bv.banner_id "
            "WHERE bv.user_id = ? AND b.media_type = 'video' AND b.is_active = 1",
            (user["id"],),
        ).fetchone()["c"]

        user_row = conn.execute("SELECT tutorials_bonus_claimed FROM users WHERE id = ?", (user["id"],)).fetchone()
        if total_videos > 0 and watched_videos >= total_videos and not user_row["tutorials_bonus_claimed"]:
            conn.execute(
                "UPDATE users SET points = points + ?, tutorials_bonus_claimed = 1 WHERE id = ?",
                (ALL_TUTORIALS_BONUS_POINTS, user["id"]),
            )
            bonus_awarded = ALL_TUTORIALS_BONUS_POINTS
            conn.commit()

    total_points = conn.execute("SELECT points FROM users WHERE id = ?", (user["id"],)).fetchone()["points"]
    conn.close()
    return jsonify(
        newly_awarded=newly_awarded,
        bonus_awarded=bonus_awarded,
        total_points=total_points,
        already_watched=bool(already),
    )


@app.get("/api/health")
def health():
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
