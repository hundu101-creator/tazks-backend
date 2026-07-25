"""
tazk's Telegram bot.

Responsibilities:
- /start opens the Mini App (with the referral code passed through, if any)
- registers a persistent menu button that opens the Mini App directly
- nothing else lives here on purpose -- all real logic (balances, tasks,
  withdrawals) belongs in the backend API, called from inside the Mini App
"""
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonWebApp,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]  # must be https:// -- see README for local tunneling
BACKEND_URL = os.environ.get("BACKEND_URL", "")  # e.g. https://tazks-backend.onrender.com
INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

PRIVACY_TEXT = (
    "Before you start, a quick privacy note:\n\n"
    "- We store your Telegram ID, name, task activity, and balance so we can "
    "pay you correctly.\n"
    "- If you share your phone number, it's used only for account support "
    "(e.g. help with a stuck withdrawal) and is never shared with third parties "
    "or other users.\n"
    "- You can ask us to delete your data at any time.\n\n"
    "Do you agree to continue?"
)


def _open_app_keyboard(ref_code: str | None):
    url = WEBAPP_URL
    if ref_code:
        url = f"{WEBAPP_URL}?startapp={ref_code}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("Open tazk's", web_app=WebAppInfo(url=url))]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ref_code = context.args[0] if context.args else None
    # stash the referral code so we still have it after the agree/contact steps
    context.user_data["ref_code"] = ref_code

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("I Agree", callback_data="privacy_agree")]]
    )
    await update.message.reply_text(PRIVACY_TEXT, reply_markup=keyboard)


async def on_privacy_agree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Thanks! One more step \u2014 please share your phone number so support can reach you if needed.")

    contact_button = KeyboardButton("Share my phone number", request_contact=True)
    await query.message.reply_text(
        "Tap the button below (this only shares the number on this Telegram account, not any other contact).",
        reply_markup=ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True),
    )


async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.effective_user.id

    # Make sure they shared THEIR OWN number, not a forwarded contact card
    # belonging to someone else.
    if contact.user_id != user_id:
        await update.message.reply_text(
            "That looks like someone else's contact card \u2014 please use the "
            "button to share your own number.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if BACKEND_URL and INTERNAL_SECRET:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{BACKEND_URL}/api/internal/set-phone",
                    json={"telegram_id": user_id, "phone": contact.phone_number},
                    headers={"X-Internal-Secret": INTERNAL_SECRET},
                )
        except httpx.HTTPError as e:
            log.warning(f"Failed to save phone to backend: {e}")

    ref_code = context.user_data.get("ref_code")
    await update.message.reply_text(
        "Verified, thank you. Tap below to open the app.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text("tazk's", reply_markup=_open_app_keyboard(ref_code))


async def post_init(application: Application):
    # Persistent button next to the message box that opens the Mini App directly
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Open tazk's", web_app=WebAppInfo(url=WEBAPP_URL))
    )


class _HealthHandler(BaseHTTPRequestHandler):
    """Does nothing except respond 200 OK, so Render's free Web Service tier
    (which requires something bound to $PORT) is satisfied. The actual bot
    logic runs separately via long-polling, not through this server."""

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, format, *args):
        pass  # silence default request logging, keep the real bot logs clean


def _run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    log.info(f"Dummy health server listening on port {port} (for Render's free tier)")
    server.serve_forever()


def main():
    # Render's free Web Service tier requires a port bound -- this thread
    # exists purely to satisfy that, it has nothing to do with the bot itself.
    threading.Thread(target=_run_dummy_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_privacy_agree, pattern="^privacy_agree$"))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))
    log.info("Bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
