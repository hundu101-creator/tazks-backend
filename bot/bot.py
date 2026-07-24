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

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]  # must be https:// -- see README for local tunneling

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    ref_code = args[0] if args else None

    url = WEBAPP_URL
    if ref_code:
        # start_param is exposed to the Mini App via Telegram.WebApp.initDataUnsafe.start_param
        url = f"{WEBAPP_URL}?startapp={ref_code}"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Open tazk's", web_app=WebAppInfo(url=url))]]
    )
    await update.message.reply_text(
        "Welcome to tazk's. Tap below to open the app.",
        reply_markup=keyboard,
    )


async def post_init(application: Application):
    # Persistent button next to the message box that opens the Mini App directly
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Open tazk's", web_app=WebAppInfo(url=WEBAPP_URL))
    )


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    log.info("Bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
