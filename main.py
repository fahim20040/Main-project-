import logging
import asyncio
import os
import time
import psutil
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web


# =========================
# CONFIG
# =========================
API_TOKEN = "8565287860:AAHqxvFGov9qwtFcmI78qVmB_KFf-24ZJ9o"
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:Ratul1234@mybotdatabase.5m5engl.mongodb.net/?retryWrites=true&w=majority"

ADMIN_ID = 6793604200
CHANNEL_ID = -1003960638119
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot"

START_TIME = time.time()


# =========================
# INIT
# =========================
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

client = AsyncIOMotorClient(MONGO_URL)
db = client["video_bot_db"]
users_col = db["users"]
video_links_col = db["video_links"]


# =========================
# WEB SERVER
# =========================
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_fake_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # VPS এর জন্য পোর্ট পরিবর্তনশীল হতে পারে, তাই default ১০০০০ রাখা হয়েছে
    port = int(os.environ.get("PORT", 10000))
    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
    except Exception as e:
        logging.error(f"Web server error: {e}")


# =========================
# HELPERS
# =========================
user_last_action = {}

async def check_user_status(user_id):
    now = time.time()
    if user_id in user_last_action:
        if now - user_last_action[user_id] < 1:
            return "spam"
    user_last_action[user_id] = now
    user = await users_col.find_one({"user_id": user_id})
    if user and user.get("is_banned"):
        return "banned"
    return "ok"

async def update_last_seen(user_id):
    # upsert: True রাখা হয়েছে যাতে নতুন ইউজার হলেও আপডেট হয়
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"last_seen": datetime.utcnow()}},
        upsert=True
    )

def get_refer_link(uid):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

async def is_subscribed(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# অটো ডিলিট ফাংশন (১০ মিনিট = ৬০০ সেকেন্ড)
async def auto_delete_video(chat_id, msg_id, seconds=600):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        # মেসেজ ইতিমধ্যে ইউজার ডিলিট করলে বা না পাওয়া গেলে যাতে এরর না দেয়
        pass


# =========================
# KEYBOARD
# =========================
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Start the bot"), KeyboardButton(text="Check your wallet")],
            [KeyboardButton(text="Buy credits"), KeyboardButton(text="Get channels")]
        ],
        resize_keyboard=True
    )


# =========================
# START COMMAND
# =========================
@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    args = command.args
    name = message.from_user.full_name

    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📁 Check Again", callback_data=f"check_{args or 'none'}")]
        ])
        # UI পরিবর্তন করা হয়নি
        await message.answer("⚠️ You must join channel first", reply_markup=kb)
        return

    # ১. ভিডিও ডেলিভারি এবং ১০ মিনিট পর অটো ডিলিট
    if args and args.startswith("vid"):
        video_data = await video_links_col.find_one({"video_key": args})
        if video_data:
            # ভিডিও পাঠানো
            sent_video = await bot.send_video(chat_id=uid, video=video_data["file_id"])
            
            # সতর্কতা মেসেজ
            notif_msg = await message.answer("⚠️ **Security Alert:** This video will be automatically deleted in **10 minutes**.")
            
            # ডিলিট টাস্ক শুরু (৬০০ সেকেন্ড)
            asyncio.create_task(auto_delete_video(uid, sent_video.message_id, 600))
            asyncio.create_task(auto_delete_video(uid, notif_msg.message_id, 600))
            return
        else:
            await message.answer("❌ Invalid or expired video link.")
            return

    # ২. ইউজার রেজিস্ট্রেশন
    user = await users_col.find_one({"user_id": uid})
    if not user:
        if args and args.startswith("ref_"):
            try:
                ref_id = int(args.split("_")[1])
                if ref_id != uid:
                    await users_col.update_one(
                        {"user_id": ref_id},
                        {"$inc": {"credits": 5}},
                        upsert=True
                    )
            except:
                pass

        await users_col.insert_one({
            "user_id": uid,
            "credits": 10,
            "name": name,
            "joined_at": datetime.utcnow()
        })

    await update_last_seen(uid)
    await message.answer(f"Welcome {name}", reply_markup=get_main_menu())


# =========================
# WALLET
# =========================
@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid}) or {}
    
    wallet_txt = (
        f"👤 **User:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {user.get('credits', 0)}\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "✨ **Note:** You can earn **10 free credits** every time you watch a short ad.\n\n"
        "💸 **Don't want to watch ads?** You can also **buy credits** directly from the button below.\n\n"
        "🎉 Let's keep the fun going!"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Refer & Earn", url=f"https://t.me/share/url?url={get_refer_link(uid)}")],
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await message.answer(wallet_txt, reply_markup=kb, parse_mode="Markdown")


# =========================
# ADMIN PANEL
# =========================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total = await users_col.count_documents({})
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    uptime = int(time.time() - START_TIME)
    text = (
        "⚡ SYSTEM STATUS\n"
        "━━━━━━━━━━━━━━\n"
        f"👥 Users: {total}\n"
        f"🖥 CPU: {cpu}%\n"
        f"🧠 RAM: {ram}%\n"
        f"⏱ Uptime: {uptime}s"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_admin")]
    ])
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "refresh_admin")
async def refresh(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    await call.answer("Updated")
    await admin_panel(call.message)


# =========================
# VIDEO SAVE (ADMIN)
# =========================
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def save_video(message: types.Message):
    key = f"vid{random.randint(1000,9999)}"
    await video_links_col.insert_one({
        "video_key": key,
        "file_id": message.video.file_id
    })
    link = f"https://t.me/{BOT_USERNAME}?start={key}"
    await message.answer(f"✅ Saved!\n{link}")


# =========================
# RUN
# =========================
async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        # VPS এ বট চালানোর জন্য polling মেথডই সবথেকে নিরাপদ
        await asyncio.gather(
            start_fake_server(),
            dp.start_polling(bot)
        )
    except Exception as e:
        logging.error(f"Bot Main loop error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
        
