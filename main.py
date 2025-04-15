import os
import logging
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler
)
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
MAX_VIDEO_SIZE = 50 * 1024 * 1024

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("أرسل رابط فيديو (YouTube، TikTok، Instagram...)")

def download_video(url: str):
    ydl_opts = {
        "format": "best[filesize<50M]",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {
                "file_path": ydl.prepare_filename(info),
                "title": info.get("title", "Video"),
                "size": info.get("filesize", 0)
            }
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    msg = update.message.reply_text("⏳ جاري التحميل...")

    video_info = download_video(url)
    if not video_info:
        msg.edit_text("❌ فشل في التحميل. تحقق من الرابط.")
        return

    try:
        with open(video_info["file_path"], "rb") as f:
            update.message.reply_video(
                video=f,
                caption=f"{video_info['title']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔁 إعادة تحميل", callback_data=f"retry_{url}")
                ]])
            )
        msg.delete()
    except Exception as e:
        logger.error(f"Upload error: {e}")
    finally:
        if os.path.exists(video_info["file_path"]):
            os.remove(video_info["file_path"])

def retry_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    url = query.data.replace("retry_", "")
    query.edit_message_text("🔄 إعادة التحميل...")
    update.message = query.message
    update.message.text = url
    handle_message(update, context)

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN not found.")
        return

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(retry_callback, pattern="^retry_"))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
