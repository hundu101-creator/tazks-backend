"""Fix 4 (F58): pages load no external scripts/styles/fonts; local assets exist; API base configurable."""
import os, re
FRONT = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
read = lambda n: open(os.path.join(FRONT, n), encoding="utf-8").read()


def test_no_external_assets():
    for page in ("index.html", "admin.html"):
        s = read(page)
        tags = re.findall(r'<(?:script|link)[^>]+(?:src|href)="([^"]+)"', s)
        assert tags, page
        for ref in tags:
            assert not re.match(r"(https?:)?//", ref), f"{page}: external {ref}"
            assert os.path.isfile(os.path.join(FRONT, ref)), f"{page}: missing {ref}"
        assert "cdn.tailwindcss.com" not in s and "fonts.googleapis" not in s and "telegram.org/js" not in s


def test_fonts_css_points_local():
    css = read("static/css/fonts.css")
    urls = re.findall(r"url\(([^)]+)\)", css)
    assert urls and all(not u.startswith("http") for u in urls)
    for u in urls:
        assert os.path.isfile(os.path.join(FRONT, "static", "css", u)), u


def test_api_base_configurable():
    for page in ("index.html", "admin.html"):
        s = read(page)
        assert "TAZKS_API_BASE" in s and 'get("api")' in s and 'loc.port === "5000" ? ""' in s


def test_size_under_limit():
    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(os.path.join(FRONT, "static")) for f in fs)
    assert total < 5 * 1024 * 1024, total
