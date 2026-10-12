"""Test setup: temp SQLite DB, fake secrets, local auth mode. Never touches backend/tazks.db,
never contacts Telegram or Render."""
import os, sys, tempfile, importlib
import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

os.environ["SKIP_AUTH_CHECK"] = "true"
os.environ["BOT_TOKEN"] = ""
os.environ["ADMIN_SECRET"] = "test-admin"
os.environ["INTERNAL_SECRET"] = "test-internal"


@pytest.fixture()
def app_mod(tmp_path, monkeypatch):
    import models
    monkeypatch.setattr(models, "DB_PATH", str(tmp_path / "test.db"))
    if "app" in sys.modules:
        mod = importlib.reload(sys.modules["app"])
    else:
        mod = importlib.import_module("app")
    mod.app.config["TESTING"] = True
    return mod


@pytest.fixture()
def client(app_mod):
    return app_mod.app.test_client()


ADMIN = {"X-Admin-Secret": "test-admin"}


def make_user(client, tg_id, ref=None):
    body = {"telegram_id": tg_id, "first_name": "T%d" % tg_id}
    if ref:
        body["ref"] = ref
    r = client.post("/api/auth", json=body)
    assert r.status_code == 200, r.get_json()
    return r.get_json()["user"]


def H(tg_id):
    return {"X-Debug-Telegram-Id": str(tg_id)}
