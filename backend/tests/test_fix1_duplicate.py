"""Fix 1 (F24): same user + same task refused while pending or approved."""
from conftest import make_user, H


def test_second_submission_refused(client):
    make_user(client, 201)
    assert client.post("/api/tasks/2/complete", headers=H(201)).status_code == 200
    r = client.post("/api/tasks/2/complete", headers=H(201))
    assert r.status_code == 409
    assert "already submitted" in r.get_json()["error"]


def test_other_task_and_other_user_still_ok(client):
    make_user(client, 202); make_user(client, 203)
    assert client.post("/api/tasks/1/complete", headers=H(202)).status_code == 200
    assert client.post("/api/tasks/3/complete", headers=H(202)).status_code == 200
    assert client.post("/api/tasks/1/complete", headers=H(203)).status_code == 200


def test_rejected_can_resubmit_approved_cannot(client, app_mod):
    import models
    make_user(client, 204)
    client.post("/api/tasks/1/complete", headers=H(204))
    conn = models.get_db()
    conn.execute("UPDATE task_completions SET status='rejected'"); conn.commit()
    assert client.post("/api/tasks/1/complete", headers=H(204)).status_code == 200
    conn.execute("UPDATE task_completions SET status='approved' WHERE status='pending_review'"); conn.commit()
    conn.close()
    r = client.post("/api/tasks/1/complete", headers=H(204))
    assert r.status_code == 409 and "approved" in r.get_json()["error"]
