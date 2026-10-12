"""Whole-app comparison for the two pages: every UI feature from TREE-TEST is still present."""
import os
FRONT = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
read = lambda n: open(os.path.join(FRONT, n), encoding="utf-8").read()

INDEX_IDS = ["view-home", "view-earn", "view-more", "view-referrals", "view-withdraw", "stat-balance",
             "stat-completed", "stat-streak", "stat-rating", "stat-points", "stat-level", "tutorials-section",
             "promo-section", "moments-section", "task-list", "claim-daily-btn", "copy-ref-btn", "ref-code",
             "payout-methods", "wd-submit", "fs-modal", "toast"]
INDEX_CALLS = ["/api/auth", "/api/state", "/api/tasks/", "/api/rewards/daily/claim", "/api/withdraw",
               "/api/banners/", "showView", "BackButton", "Telegram?.WebApp", "tg?.ready()", "tg?.expand()"]
ADMIN_IDS = ["login-screen", "secret-input", "admin-panel", "add-task-btn", "task-table", "add-banner-btn",
             "banner-table"]
ADMIN_CALLS = ["/api/admin/tasks", "/api/admin/banners", "X-Admin-Secret"]


def test_index_features_present():
    s = read("index.html")
    for i in INDEX_IDS:
        assert f'id="{i}"' in s, i
    for c in INDEX_CALLS:
        assert c in s, c
    for v in ("home", "earn", "more", "referrals", "withdraw"):
        assert f'data-view="{v}"' in s


def test_admin_features_present():
    s = read("admin.html")
    for i in ADMIN_IDS:
        assert f'id="{i}"' in s, i
    for c in ADMIN_CALLS:
        assert c in s, c
