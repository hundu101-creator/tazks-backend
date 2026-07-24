# tazk's Telegram Mini App

Three separate pieces. Each runs on its own, and they talk to each other over HTTP.

```
frontend/   the app itself -- what opens inside Telegram (index.html, plain JS)
backend/    the API + database -- balances, tasks, withdrawals (Python/Flask + SQLite)
bot/        the Telegram bot -- its only job is to open the frontend (Python)
```

## How each piece works

### 1. bot/bot.py -- the door
This is NOT where any app logic lives. It does exactly two things:
- `/start` replies with a button that opens your Mini App URL inside Telegram
- Sets a persistent "Open tazk's" menu button next to the chat's message box

If someone starts the bot via a referral link (`t.me/yourbot?start=CODE`), the code
after `?start=` gets forwarded into the Mini App URL as `?startapp=CODE`, and the
frontend hands it back to Telegram, which exposes it to your backend as
`start_param` inside `initData` -- that's how referral attribution flows through
end-to-end without you having to build your own deep-link system.

### 2. backend/app.py -- the source of truth
A Flask API with SQLite behind it. Every route that touches money re-verifies the
request came from a real Telegram session, using `telegram_auth.py`, which
replicates Telegram's own HMAC check
(https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).
This matters: without it, anyone could call your API with someone else's
`telegram_id` and see or spend their balance.

Key design choices you should know about, all deliberate:
- **Task completions go in as `pending_review`, not auto-paid.** Nothing credits
  a balance just because the frontend says "task done" -- you decide what actually
  verifies a task (e.g. a callback from a real ad network or survey partner)
  before money moves.
- **Withdrawals are always created as `pending`.** The balance isn't touched until
  you (or an admin panel you build later) approve it. There's no code path that
  auto-approves a payout.
- **Referral bonus is stored as `0.0` until you decide the real payout rule.** I
  didn't invent a number for "how much a referral is worth" -- that's a real
  business decision with real money attached to it.

### 3. frontend/index.html -- the interface
One HTML file, five views (Home / Earn / More / Referrals / Withdraw) toggled by
JS instead of separate pages -- Telegram Mini Apps work better as an SPA. It loads
`telegram-web-app.js` (Telegram's own SDK), which gives it:
- `tg.initData` -- signed proof of who's using it, sent to the backend on every
  call as the `X-Telegram-Init-Data` header
- `tg.expand()` -- opens the app full-height instead of a small sheet
- `tg.BackButton` -- wired up so Telegram's native back button matches your tabs

On load it calls `/api/auth` (creates the user on first visit), then `/api/state`
(fills in every screen), then re-fetches state after any action that changes it.

## What you need to prepare

**1. A public HTTPS URL for the backend.** Telegram Mini Apps refuse plain HTTP
and refuse localhost. Cheapest paths:
- [Railway](https://railway.app) or [Render](https://render.com) -- push the
  `backend/` folder, both give you a free HTTPS URL
- Or `ngrok http 5000` while developing, to get a temporary HTTPS tunnel to your
  own machine

**2. A public HTTPS URL for the frontend.** Same constraint. Easiest option:
GitHub Pages, Netlify, or Vercel -- drag in `frontend/index.html`, done. (It's a
static file, no build step.)

**3. Your bot token**, which you already have. Put it in `bot/.env` and
`backend/.env` (copy `.env.example` in each folder and fill it in).

**4. Two small edits once you have real URLs:**
- In `frontend/index.html`, replace `YOUR-BACKEND-DOMAIN` with your deployed
  backend URL, and `YOUR_BOT_USERNAME` with your bot's actual @username
- In `bot/.env`, set `WEBAPP_URL` to your deployed frontend URL

## Running it locally first (recommended before deploying)

```bash
# backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # fill in BOT_TOKEN, set SKIP_AUTH_CHECK=true for now
python3 app.py                 # runs on http://localhost:5000

# frontend -- just open frontend/index.html in a browser
# (SKIP_AUTH_CHECK=true lets you test the API without a real Telegram session --
#  turn it back to false before deploying, or auth is wide open)

# bot -- only works with a real public WEBAPP_URL, so do this after deploying
cd bot
pip install python-telegram-bot python-dotenv
cp .env.example .env           # fill in BOT_TOKEN and WEBAPP_URL
python3 bot.py
```

## Before you take real money through this

The withdrawal and referral flows are wired up honestly (nothing auto-pays,
nothing is fabricated), but the original design template included a "Live Feed"
of other users' withdrawals and a "Top Earners" leaderboard that were just
placeholder copy, not real data. I left those views out of the rebuilt frontend
rather than build fake social proof into a money app -- worth deciding
deliberately if/how you want real versions of those (e.g. showing your actual
top referrers once you have some).
