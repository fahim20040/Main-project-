import logging
import asyncio
import os
import time
import psutil
import random
import uuid
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.exceptions import TelegramBadRequest

from motor.motor_asyncio import AsyncIOMotorClient

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
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Subscription check error for {user_id}: {e}")
        return False

async def auto_delete_video(chat_id, msg_id, seconds=600):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception as e:
        logging.error(f"Auto delete failed: {e}")

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Start the bot"), KeyboardButton(text="Check your wallet")],
            [KeyboardButton(text="Buy credits"), KeyboardButton(text="Get channels")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# =========================
# HANDLERS
# =========================

@dp.callback_query(F.data.startswith("check_"))
async def check_subscription_callback(call: types.CallbackQuery):
    uid = call.from_user.id
    try:
        if await is_subscribed(uid):
            await call.answer("✅ Thank you for joining!", show_alert=False)
            await call.message.delete()
            await bot.send_message(uid, f"Welcome back, {call.from_user.full_name}!", reply_markup=get_main_menu())
        else:
            await call.answer("⚠️ You still haven't joined the channel!", show_alert=True)
    except Exception as e:
        await call.answer("❌ Error occurred!", show_alert=True)

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    args = command.args or ""
    name = message.from_user.full_name

    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📂 Check Again", callback_data=f"check_{args or 'none'}")]
        ])
        await message.answer("⚠️ You must join our channel first to use the bot!", reply_markup=kb)
        return

    if args and args.startswith("vid"):
        user = await users_col.find_one({"user_id": uid})
        if not user or user.get("credits", 0) < 1:
            await message.answer("❌ আপনার পর্যাপ্ত ক্রেডিট নেই!")
            return

        video_data = await video_links_col.find_one({"video_key": args})
        if video_data:
            await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
            sent_video = await bot.send_video(chat_id=uid, video=video_data["file_id"])
            notif_msg = await message.answer("⚠️ Video will be deleted in 10 mins.")
            asyncio.create_task(auto_delete_video(uid, sent_video.message_id, 600))
            asyncio.create_task(auto_delete_video(uid, notif_msg.message_id, 600))
            return

    user = await users_col.find_one({"user_id": uid})
    if not user:
        credits = 10
        if args and args.startswith("ref_"):
            try:
                ref_id = int(args.split("_")[1])
                if ref_id != uid:
                    await users_col.update_one({"user_id": ref_id}, {"$inc": {"credits": 5}})
                    try: await bot.send_message(ref_id, "🎉 Someone joined! +5 credits.")
                    except: pass
                    credits += 2
            except: pass
        
        await users_col.insert_one({"user_id": uid, "credits": credits, "name": name, "joined_at": datetime.utcnow()})

    await message.answer(f"🎉 Welcome {name}!", reply_markup=get_main_menu())

@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    credits = user.get("credits", 0) if user else 0
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Refer & Earn", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start=ref_{uid}")],
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    
    await message.answer(f"👤 **User:** {message.from_user.full_name}\n💰 **Credits:** {credits}", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.video)
async def handle_admin_video(message: types.Message):
    if not is_admin(message.from_user.id): return
    file_id = message.video.file_id
    video_key = f"vid_{str(uuid.uuid4())[:8]}"
    await video_links_col.insert_one({"video_key": video_key, "file_id": file_id, "created_at": datetime.utcnow()})
    await message.answer(f"✅ Video Saved!\n🔗 Link: `https://t.me/{BOT_USERNAME}?start={video_key}`", parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
