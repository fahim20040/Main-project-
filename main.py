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
API_TOKEN = os.getenv("8565287860:AAHqxvFGov9qwtFcmI78qVmB_KFf-24ZJ9o")
MONGO_URL = os.getenv("mongodb+srv://itsmeratul3_db_user:<db_password>@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")

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
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()


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
    except:
        return False


async def auto_delete(chat_id, msg_id):
    await asyncio.sleep(300)
    try:
        await bot.delete_message(chat_id, msg_id)
    except:
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
        await message.answer("⚠️ You must join channel first", reply_markup=kb)
        return

    user = await users_col.find_one({"user_id": uid})

    if not user:
        if args and args.startswith("ref_"):
            ref_id = int(args.split("_")[1])
            if ref_id != uid:
                await users_col.update_one(
                    {"user_id": ref_id},
                    {"$inc": {"credits": 5}},
                    upsert=True
                )

        await users_col.insert_one({
            "user_id": uid,
            "credits": 10,
            "name": name
        })

    await update_last_seen(uid)
    await message.answer(f"Welcome {name}", reply_markup=get_main_menu())


# =========================
# WALLET (FULL UI RESTORED)
# =========================
@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})

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
        [
            InlineKeyboardButton(
                text="🤝 Refer & Earn",
                url=f"https://t.me/share/url?url={get_refer_link(uid)}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💎 Buy Credits",
                url=f"https://t.me/{ADMIN_USERNAME}"
            )
        ]
    ])

    await message.answer(wallet_txt, reply_markup=kb, parse_mode="Markdown")


# =========================
# OUT OF CREDITS (FULL BEAUTIFUL UI)
# =========================
def out_of_credit_message():
    return (
        "🚨 **Oops! You're out of credits!** 🥲\n\n"
        "💡 But don't worry — getting more is super easy:\n"
        "1️⃣ Tap the button below 👇\n"
        "2️⃣ Complete a quick task ✅\n"
        "3️⃣ Instantly receive **10 free credits** to use the bot! 🚀\n\n"
        "🆓 100% FREE — every single time!\n"
        "🔄 You can earn **10 credits** again and again!\n\n"
        "📌 **Need help?** Check out our tutorial guide!\n\n"
        "🛠 **Facing issues?** Message support from admin.\n\n"
        "Let's keep the fun going! 🎉💥"
    )


def out_of_credit_buttons(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚀 Refer & Earn 5 Credits",
                url=f"https://t.me/share/url?url={get_refer_link(uid)}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❓ How to Use Bot",
                url="https://t.me/genzexposed"
            )
        ]
    ])


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

async def start_fake_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is Running"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    

# =========================
# RUN
# =========================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        start_fake_server(),
        dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())
