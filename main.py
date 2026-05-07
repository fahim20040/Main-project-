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
# HELPERS
# =========================
async def is_subscribed(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def auto_delete_video(chat_id, msg_id, seconds=600):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Start the bot"), KeyboardButton(text="Check your wallet")],
            [KeyboardButton(text="Buy credits"), KeyboardButton(text="Get channels")]
        ],
        resize_keyboard=True
    )

def get_refer_link(uid):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

# =========================
# HANDLERS
# =========================

# ১. 'Check Again' বাটন হ্যান্ডলার (এটি আপনার আগের কোডে ছিল না)
@dp.callback_query(F.data.startswith("check_"))
async def check_subscription_callback(call: types.CallbackQuery):
    uid = call.from_user.id
    arg = call.data.replace("check_", "")
    
    if await is_subscribed(uid):
        await call.answer("✅ Thank you for joining!")
        # সাবস্ক্রাইব করা থাকলে স্টার্ট মেসেজ পাঠিয়ে দিচ্ছি
        await call.message.delete()
        # এখানে স্টার্ট কমান্ডের মতো লজিক কাজ করবে
        await bot.send_message(uid, f"Welcome back, {call.from_user.full_name}!", reply_markup=get_main_menu())
    else:
        await call.answer("⚠️ You still haven't joined the channel!", show_alert=True)

# ২. স্টার্ট কমান্ড
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

    # ভিডিও ডেলিভারি
    if args and args.startswith("vid"):
        video_data = await video_links_col.find_one({"video_key": args})
        if video_data:
            sent_video = await bot.send_video(chat_id=uid, video=video_data["file_id"])
            notif_msg = await message.answer("⚠️ **Security Alert:** This video will be deleted in **10 minutes**.")
            asyncio.create_task(auto_delete_video(uid, sent_video.message_id, 600))
            asyncio.create_task(auto_delete_video(uid, notif_msg.message_id, 600))
            return

    # ইউজার রেজিস্ট্রেশন ও রেফার
    user = await users_col.find_one({"user_id": uid})
    if not user:
        credits = 10
        if args and args.startswith("ref_"):
            try:
                ref_id = int(args.split("_")[1])
                if ref_id != uid:
                    await users_col.update_one({"user_id": ref_id}, {"$inc": {"credits": 5}})
                    await bot.send_message(ref_id, "🎉 Someone joined using your link! You got 5 credits.")
            except: pass
        
        await users_col.insert_one({
            "user_id": uid, "credits": credits, "name": name, "joined_at": datetime.utcnow()
        })

    await message.answer(f"Welcome {name}", reply_markup=get_main_menu())

# ৩. ওয়ালেট হ্যান্ডলার (মেনু বাটন ফিক্সড)
@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid}) or {"credits": 0}
    
    wallet_txt = (
        f"👤 **User:** {message.from_user.full_name}\n🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {user.get('credits', 0)}\n\n"
        "✨ Note: Earn 10 free credits by watching ads.\n"
        "💸 Buy credits from admin below."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Refer & Earn", url=f"https://t.me/share/url?url={get_refer_link(uid)}")],
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await message.answer(wallet_txt, reply_markup=kb, parse_mode="Markdown")

# ৪. ক্রেডিট অ্যাড কমান্ড (এডমিন কমান্ড যা আপনার দরকার ছিল)
@dp.message(Command("add"))
async def add_credits(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id = int(args[0])
        amount = int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}}, upsert=True)
        await message.answer(f"✅ Added {amount} credits to `{target_id}`")
        await bot.send_message(target_id, f"💰 {amount} credits have been added to your wallet!")
    except:
        await message.answer("❌ Format: `/add [user_id] [amount]`")

# ৫. এডমিন প্যানেল
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total = await users_col.count_documents({})
    uptime = int(time.time() - START_TIME)
    text = f"⚡ SYSTEM STATUS\n👥 Users: {total}\n🖥 CPU: {psutil.cpu_percent()}%\n⏱ Uptime: {uptime}s"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_admin")]])
    await message.answer(text, reply_markup=kb)

# =========================
# RUN BOT
# =========================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
