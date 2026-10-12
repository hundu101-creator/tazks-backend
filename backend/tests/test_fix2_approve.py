"""Fix 2: admin approves/rejects a pending submission; approve credits reward exactly once."""
from conftest import ADMIN, make_user, H


def _submit(client, tg, task=1):
    make_user(client, tg)
    assert client.post(f"/api/tasks/{task}/complete", headers=H(tg)).status_code == 200
    rows = client.get("/api/admin/completions", headers=ADMIN).get_json()["completions"]
    return [r for r in rows if r["telegram_id"] == tg][0]


def bal(client, tg):
    return client.get("/api/state", headers=H(tg)).get_json()["user"]


def test_needs_admin_secret(client):
    c = _submit(client, 301)
    assert client.get("/api/admin/completions").status_code == 401
    assert client.post(f"/api/admin/completions/{c['id']}/approve").status_code == 401
    assert client.post(f"/api/admin/completions/{c['id']}/approve", headers={"X-Admin-Secret": "x"}).status_code == 401
    assert bal(client, 301)["balance"] == 0


def test_approve_credits_once(client):
    c = _submit(client, 302)
    assert c["status"] == "pending_review" and c["reward"] == 1.0
    r = client.post(f"/api/admin/completions/{c['id']}/approve", headers=ADMIN)
    assert r.status_code == 200 and r.get_json()["credited"] == 1.0
    u = bal(client, 302)
    assert u["balance"] == 1.0 and u["completed_tasks"] == 1
    assert client.post(f"/api/admin/completions/{c['id']}/approve", headers=ADMIN).status_code == 409
    assert client.post(f"/api/admin/completions/{c['id']}/reject", headers=ADMIN).status_code == 409
    assert bal(client, 302)["balance"] == 1.0
    # approved task cannot be resubmitted (fix 1)
    assert client.post("/api/tasks/1/complete", headers=H(302)).status_code == 409
    assert client.get("/api/admin/completions?status=pending_review", headers=ADMIN).get_json()["completions"] == []
    assert len(client.get("/api/admin/completions?status=approved", headers=ADMIN).get_json()["completions"]) == 1


def test_reject_no_credit_and_resubmit(client):
    c = _submit(client, 303)
    assert client.post(f"/api/admin/completions/{c['id']}/reject", headers=ADMIN).status_code == 200
    assert bal(client, 303)["balance"] == 0
    assert client.post(f"/api/admin/completions/{c['id']}/approve", headers=ADMIN).status_code == 409
    assert client.post("/api/tasks/1/complete", headers=H(303)).status_code == 200


def test_unknown_id_404(client):
    assert client.post("/api/admin/completions/9999/approve", headers=ADMIN).status_code == 404
