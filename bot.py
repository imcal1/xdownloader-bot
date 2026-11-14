import os, re, asyncio, tempfile, uuid, shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, filters)
import yt_dlp

TOKEN = os.environ["BOT_TOKEN"]
BOT_USER = "@XTwitterVidDL_bot"
DEMO_VIDEO = ""  # put demo video file_id here later
MAX_MB = 50
X_LINK = re.compile(
    r"https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/\S+/status/\d+\S*", re.I)
INVITE_URL = ("https://t.me/share/url?url=https://t.me/XTwitterVidDL_bot"
              "&text=Download%20X%20(Twitter)%20videos%20fast")
HOW_TO = ("🔗 Send me a link\nto any X (Twitter) video post, and I'll "
          "send the video in a few seconds.\n\n"
          "📄 Tap \"Get description\" under the video to get the tweet text.")

def invite_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔗 Invite a friend", url=INVITE_URL)]])

async def start(update: Update, context):
    await update.message.reply_text("How to use the bot? 👇")
    if DEMO_VIDEO:
        await update.message.reply_video(
            DEMO_VIDEO, caption=HOW_TO, reply_markup=invite_kb())
    else:
        await update.message.reply_text(HOW_TO, reply_markup=invite_kb())

def download(url, folder):
    opts = {
        "outtmpl": os.path.join(folder, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4][filesize<50M]/best[ext=mp4]/best",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    path = os.path.join(folder, os.listdir(folder)[0])
    return info, path

async def handle_link(update: Update, context):
    m = X_LINK.search(update.message.text or "")
    if not m:
        await update.message.reply_text(
            "Please send a valid X (Twitter) link.")
        return
    wait = await update.message.reply_text("⏳ Downloading...")
    folder = tempfile.mkdtemp()
    try:
        info, path = await asyncio.to_thread(download, m.group(0), folder)
        if os.path.getsize(path) > MAX_MB * 1024 * 1024:
            await wait.edit_text(
                "Sorry, this video is too big for Telegram (over 50MB).")
            return
        key = uuid.uuid4().hex[:10]
        context.bot_data[key] = (info.get("description")
                                 or info.get("title") or "No description.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(
            "📄 Get description", callback_data="d:" + key)]])
        with open(path, "rb") as f:
            await update.message.reply_video(
                f, caption=BOT_USER, reply_markup=kb,
                supports_streaming=True,
                read_timeout=120, write_timeout=120)
        await wait.delete()
    except Exception as e:
        print("ERROR:", e)
        await wait.edit_text(
            "Could not download this video. Make sure the post has a "
            "video and is public.")
    finally:
        shutil.rmtree(folder, ignore_errors=True)

async def desc_cb(update: Update, context):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    text = context.bot_data.get(
        key, "Description no longer available. Please send the link again.")
    await q.message.reply_text(text[:4000])

def main():
    app = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30).get_updates_connect_timeout(30).get_updates_read_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(desc_cb, pattern="^d:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()

main()
