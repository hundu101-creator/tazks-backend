// Fix 3 smoke: runs index.html's script against a fake DOM + fake Telegram.WebApp.
// node frontend/tests/backbutton_smoke.js   (no network, no browser)
const fs = require("fs"), path = require("path"), vm = require("vm");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join("\n");
const ids = [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]);
const views = [...html.matchAll(/data-view="([^"]+)"/g)].map(m => m[1]);

function el(id, extra = {}) {
  const cls = new Set(id === "view-home" ? ["view", "active"] : id.startsWith("view-") ? ["view"] : id === "fs-modal" ? ["hidden"] : []);
  const listeners = {};
  return Object.assign({ id, dataset: {}, style: {}, textContent: "", innerHTML: "", value: "", src: "",
    classList: { add: c => cls.add(c), remove: c => cls.delete(c), contains: c => cls.has(c),
      toggle: (c, on) => (on === undefined ? (cls.has(c) ? cls.delete(c) : cls.add(c)) : on ? cls.add(c) : cls.delete(c)) },
    _cls: cls, addEventListener: (t, f) => (listeners[t] = f), click: () => listeners.click && listeners.click({ preventDefault() {} }),
    querySelectorAll: () => [], appendChild() {} }, extra);
}
const els = Object.fromEntries(ids.map(i => [i, el(i)]));
const navLinks = views.map(v => { const e = el("nav-" + v); e.dataset.view = v; return e; });
const viewEls = ids.filter(i => i.startsWith("view-")).map(i => els[i]);
let backHandler = null, backVisible = false;
const tg = { initData: "", ready() {}, expand() {}, BackButton: { show() { backVisible = true; }, hide() { backVisible = false; }, onClick(f) { backHandler = f; } } };
const document = {
  getElementById: i => els[i] || (els[i] = el(i)),
  querySelectorAll: q => q === ".view" ? viewEls : q === ".nav-link" ? navLinks : [],
  querySelector: () => null, createElement: () => el("x"),
};
const ctx = { window: { Telegram: { WebApp: tg }, location: { hostname: "127.0.0.1", port: "8080", protocol: "http:", origin: "http://127.0.0.1:8080", search: "" } },
  document, console, setTimeout, clearInterval, setInterval: () => 0, navigator: {}, URLSearchParams,
  fetch: async () => ({ ok: false, status: 503, json: async () => ({ error: "offline test" }) }) };
ctx.window.document = document; ctx.location = ctx.window.location;
vm.createContext(ctx); vm.runInContext(script, ctx);

const active = () => viewEls.find(v => v._cls.has("active")).id;
const nav = v => navLinks.find(a => a.dataset.view === v).click();
let fails = 0; const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) fails++; };
ok(typeof backHandler === "function", "BackButton.onClick handler registered");
nav("earn"); ok(active() === "view-earn" && backVisible, "earn shown, BackButton visible");
nav("withdraw"); ok(active() === "view-withdraw", "withdraw shown");
backHandler(); ok(active() === "view-earn" && backVisible, "back -> earn (previous screen)");
backHandler(); ok(active() === "view-home" && !backVisible, "back -> home, BackButton hidden");
backHandler(); ok(active() === "view-home" && !backVisible, "back on home stays home");
nav("more"); nav("home"); ok(!backVisible, "nav to home hides BackButton");
nav("referrals"); els["fs-modal"]._cls.delete("hidden"); backHandler();
ok(els["fs-modal"]._cls.has("hidden") && active() === "view-referrals", "back closes fullscreen video first");
process.exit(fails ? 1 : 0);
