"""Whole-app comparison: every endpoint/feature that worked in TREE-TEST-2026-10-12
(tree C, b7c7422) must still work. Any failure here = lost feature."""
import sqlite3
from conftest import ADMIN, make_user, H


def test_health(client):
    assert client.get("/api/health").get_json() == {"ok": True}


def test_seed_and_state(client):
    make_user(client, 101)
    s = client.get("/api/state", headers=H(101)).get_json()
    for k in ("user", "tasks", "banners", "watched_banner_ids", "daily", "referrals", "recent_signups"):
        assert k in s
    assert len(s["tasks"]) == 4
    assert s["referrals"]["code"].startswith("TZK")


def test_state_without_id_401(client):
    assert client.get("/api/state").status_code == 401


def test_forged_initdata_401(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, "SKIP_AUTH_CHECK", False)
    monkeypatch.setattr(app_mod, "BOT_TOKEN", "123:fake")
    r = client.post("/api/auth", headers={"X-Telegram-Init-Data": "user=%7B%22id%22%3A1%7D&hash=bad"})
    assert r.status_code == 401
    assert client.get("/api/state", headers={"X-Telegram-Init-Data": "hash=bad"}).status_code == 401


def test_referral_row(client, app_mod):
    a = make_user(client, 102)
    make_user(client, 103, ref=a["referral_code"])
    s = client.get("/api/state", headers=H(102)).get_json()
    assert s["referrals"]["count"] == 1


def test_privacy_accept(client):
    make_user(client, 104)
    assert client.post("/api/privacy/accept", headers=H(104)).status_code == 200
    assert client.get("/api/state", headers=H(104)).get_json()["user"]["privacy_accepted_at"]


def test_task_submit_pending_no_credit(client):
    make_user(client, 105)
    r = client.post("/api/tasks/1/complete", headers=H(105))
    assert r.status_code == 200 and r.get_json()["status"] == "submitted_for_review"
    assert client.get("/api/state", headers=H(105)).get_json()["user"]["balance"] == 0
    assert client.post("/api/tasks/999/complete", headers=H(105)).status_code == 404
    assert client.post("/api/tasks/1/complete").status_code == 401


def test_daily_claim_once(client):
    make_user(client, 106)
    r = client.post("/api/rewards/daily/claim", headers=H(106))
    assert r.status_code == 200 and r.get_json()["reward"] == 0.5
    assert client.post("/api/rewards/daily/claim", headers=H(106)).status_code == 400
    assert client.get("/api/state", headers=H(106)).get_json()["user"]["balance"] == 0.5


def test_withdraw_limits(client):
    make_user(client, 107)
    w = lambda a: client.post("/api/withdraw", headers=H(107), json={"amount": a, "method": "M-Pesa", "account": "x"})
    assert w(5).status_code == 400
    assert w(50).status_code == 400
    assert client.post("/api/withdraw", headers=H(107), json={}).status_code == 400


def test_set_phone(client):
    make_user(client, 108)
    body = {"telegram_id": 108, "phone": "+251900000000"}
    assert client.post("/api/internal/set-phone", json=body).status_code == 401
    assert client.post("/api/internal/set-phone", json=body,
                       headers={"X-Internal-Secret": "test-internal"}).status_code == 200


def test_admin_tasks_crud(client):
    assert client.get("/api/admin/tasks").status_code == 401
    assert client.get("/api/admin/tasks", headers={"X-Admin-Secret": "wrong"}).status_code == 401
    assert len(client.get("/api/admin/tasks", headers=ADMIN).get_json()["tasks"]) == 4
    t = {"title": "T", "description": "D", "category": "c", "reward_min": 1, "reward_max": 2}
    assert client.post("/api/admin/tasks", headers=ADMIN, json=t).status_code == 200
    assert client.post("/api/admin/tasks", headers=ADMIN, json={}).status_code == 400
    tasks = client.get("/api/admin/tasks", headers=ADMIN).get_json()["tasks"]
    tid = tasks[0]["id"]
    t["is_active"] = False
    assert client.put(f"/api/admin/tasks/{tid}", headers=ADMIN, json=t).status_code == 200
    assert client.delete(f"/api/admin/tasks/{tid}", headers=ADMIN).status_code == 200
    assert len(client.get("/api/admin/tasks", headers=ADMIN).get_json()["tasks"]) == 4


def test_banners_and_tutorial_points(client):
    assert client.get("/api/admin/banners").status_code == 401
    for i in range(2):
        b = {"title": f"V{i}", "media_type": "video", "link_url": "https://youtu.be/aaaaaaaaaaa", "points": 10}
        assert client.post("/api/admin/banners", headers=ADMIN, json=b).status_code == 200
    bs = client.get("/api/admin/banners", headers=ADMIN).get_json()["banners"]
    assert len(bs) == 2
    make_user(client, 109)
    r1 = client.post(f"/api/banners/{bs[0]['id']}/watch", headers=H(109)).get_json()
    assert r1["newly_awarded"] == 10
    assert client.post(f"/api/banners/{bs[0]['id']}/watch", headers=H(109)).get_json()["already_watched"]
    r3 = client.post(f"/api/banners/{bs[1]['id']}/watch", headers=H(109)).get_json()
    assert r3["bonus_awarded"] == 50 and r3["total_points"] == 70
    b0 = dict(bs[0]); b0["is_active"] = False
    assert client.put(f"/api/admin/banners/{b0['id']}", headers=ADMIN, json=b0).status_code == 200
    # delete an unwatched banner (deleting a watched one hits a pre-existing FK error, not in scope)
    client.post("/api/admin/banners", headers=ADMIN, json={"title": "P", "media_type": "photo", "image_url": "x.png"})
    pid = [b for b in client.get("/api/admin/banners", headers=ADMIN).get_json()["banners"] if b["title"] == "P"][0]["id"]
    assert client.delete(f"/api/admin/banners/{pid}", headers=ADMIN).status_code == 200
