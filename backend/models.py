"""
Database layer for the tazk's Mini App backend.
Plain sqlite3 (no ORM) so it's easy to read and easy to swap out later.
"""
import sqlite3
import os
import secrets
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tazks.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    balance REAL NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    rating REAL NOT NULL DEFAULT 5.0,
    referral_code TEXT UNIQUE NOT NULL,
    referred_by INTEGER REFERENCES users(id),
    daily_streak INTEGER NOT NULL DEFAULT 0,
    last_daily_claim TEXT,
    phone TEXT,
    privacy_accepted_at TEXT,
    phone_verified_at TEXT,
    points INTEGER NOT NULL DEFAULT 0,
    tutorials_bonus_claimed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    tag TEXT,
    reward_min REAL NOT NULL,
    reward_max REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS task_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    reward REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending review / approved / rejected
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount REAL NOT NULL,
    method TEXT NOT NULL,
    account TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending / approved / rejected / paid
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referral_bonuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL REFERENCES users(id),
    referred_id INTEGER NOT NULL REFERENCES users(id),
    bonus REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS banners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    link_url TEXT,          -- video: a YouTube link. photo/gif: usually unused
    media_type TEXT NOT NULL DEFAULT 'link',  -- 'video' | 'photo' | 'gif' | 'link'
    points INTEGER NOT NULL DEFAULT 0,        -- awarded once per user for 'video' type
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS banner_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    banner_id INTEGER NOT NULL REFERENCES banners(id),
    points INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, banner_id)   -- points can only be earned once per video per user
);
"""

SEED_TASKS = [
    ("Join Telegram Groups", "Support emerging communities and crypto projects by joining their official channels.", "social", "High Yield", 1.0, 5.0),
    ("Join WhatsApp Groups", "Participate in focused discussion groups and market research circles.", "social", "Instant Pay", 0.5, 2.5),
    ("Watch Ads", "Earn micro-rewards for every video ad or promotional content viewed completely.", "ads", "Unlimited", 0.10, 0.50),
    ("Data Collection & Polls", "Share your opinions on products and services to help brands improve.", "surveys", "Top Choice", 1.0, 15.0),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn):
    """Adds columns to already-existing tables from before these fields
    existed. SQLite has no 'ADD COLUMN IF NOT EXISTS', so we just try each
    and ignore the error if it's already there."""
    for col_def in ("phone TEXT", "privacy_accepted_at TEXT", "phone_verified_at TEXT",
                    "points INTEGER NOT NULL DEFAULT 0", "tutorials_bonus_claimed INTEGER NOT NULL DEFAULT 0"):
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass  # column already exists
    for col_def in ("media_type TEXT NOT NULL DEFAULT 'link'", "points INTEGER NOT NULL DEFAULT 0"):
        try:
            conn.execute(f"ALTER TABLE banners ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    _migrate(conn)
    count = conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"]
    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title, description, category, tag, reward_min, reward_max) VALUES (?,?,?,?,?,?)",
            SEED_TASKS,
        )
    conn.commit()
    conn.close()


def gen_referral_code(telegram_id: int) -> str:
    return f"TZK{telegram_id % 100000}{secrets.token_hex(2).upper()}"


def get_or_create_user(telegram_id: int, username: str, first_name: str, referred_by_code: str | None):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    if row:
        conn.close()
        return dict(row)

    referred_by_id = None
    if referred_by_code:
        ref_row = conn.execute("SELECT * FROM users WHERE referral_code = ?", (referred_by_code,)).fetchone()
        if ref_row:
            referred_by_id = ref_row["id"]

    code = gen_referral_code(telegram_id)
    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO users (telegram_id, username, first_name, balance, completed_tasks, rating, "
        "referral_code, referred_by, created_at) VALUES (?,?,?,0,0,5.0,?,?,?)",
        (telegram_id, username, first_name, code, referred_by_id, now),
    )
    conn.commit()
    new_id = cur.lastrowid

    # NOTE: referral bonus is only credited once, and is a REAL ledger entry
    # (not a fabricated number) so it can be audited later.
    if referred_by_id:
        conn.execute(
            "INSERT INTO referral_bonuses (referrer_id, referred_id, bonus, created_at) VALUES (?,?,?,?)",
            (referred_by_id, new_id, 0.0, now),  # bonus set to 0 until you decide the real payout rule
        )
        conn.commit()

    row = conn.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)
