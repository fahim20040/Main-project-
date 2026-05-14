import logging
import asyncio
import os
import time
import psutil
import random
import uuid  
from datetime import datetime, timedelta

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
API_TOKEN = "8565287860:AAEuYopIrpt9UtZLXMLxC_ceo5z-fOTsT8M"
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:Ratul1234@mybotdatabase.5m5engl.mongodb.net/?retryWrites=true&w=majority"

ADMIN_ID = 6793604200 
CHANNEL_ID = -1003960638119
LOG_CHANNEL_ID = -1003943039065  # <--- আপনার দেওয়া গ্রুপ আইডি এখানে বসানো হয়েছে
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
async def send_log(text):
    """লগ চ্যানেলে ট্রানজেকশন হিস্ট্রি পাঠানোর ফাংশন"""
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Log error: {e}")

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
            [KeyboardButton(text="🎁 Claim Free Credit"), KeyboardButton(text="Get channels")]
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
    name = call.from_user.full_name
    args = call.data.replace("check_", "")
    
    try:
        if await is_subscribed(uid):
            user_data = await users_col.find_one({"user_id": uid})
            if not user_data:
                credits = 10
                log_msg = f"🆕 **New User Registered**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`"
                if args.startswith("ref_"):
                    try:
                        ref_id = int(args.split("_")[1])
                        if ref_id != uid:
                            await users_col.update_one({"user_id": ref_id}, {"$inc": {"credits": 5}})
                            try: await bot.send_message(ref_id, f"🎉 {name} আপনার লিঙ্কে জয়েন করেছে! আপনি ৫ ক্রেডিট পেয়েছেন।")
                            except: pass
                            credits += 2
                            log_msg += f"\n🤝 **Referrer ID:** `{ref_id}` (Got 5 credits)"
                    except: pass
                await users_col.insert_one({"user_id": uid, "credits": credits, "name": name, "joined_at": datetime.utcnow()})
                await send_log(log_msg)
            
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

    user_data = await users_col.find_one({"user_id": uid})
    if user_data and user_data.get("is_banned"):
        await message.answer("🚫 আপনি এই বটটি ব্যবহার করার জন্য নিষিদ্ধ (Banned)।")
        return

    if not user_data and await is_subscribed(uid):
        credits = 10
        log_msg = f"🆕 **New User Registered**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`"
        if args.startswith("ref_"):
            try:
                ref_id = int(args.split("_")[1])
                if ref_id != uid:
                    await users_col.update_one({"user_id": ref_id}, {"$inc": {"credits": 5}})
                    try: await bot.send_message(ref_id, f"🎉 {name} আপনার লিঙ্কে জয়েন করেছে! আপনি ৫ ক্রেডিট পেয়েছেন।")
                    except: pass
                    credits += 2
                    log_msg += f"\n🤝 **Referrer ID:** `{ref_id}` (Got 5 credits)"
            except: pass
        await users_col.insert_one({"user_id": uid, "credits": credits, "name": name, "joined_at": datetime.utcnow()})
        await send_log(log_msg)
        user_data = await users_col.find_one({"user_id": uid})

    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📂 Check Again", callback_data=f"check_{args or 'none'}")]
        ])
        await message.answer("⚠️ You must join our channel first to use the bot!", reply_markup=kb)
        return

    if args.startswith("vid"):
        if not user_data or user_data.get("credits", 0) < 1:
            await message.answer("❌ আপনার পর্যাপ্ত ক্রেডিট নেই! ভিডিও দেখতে ক্রেডিট অর্জন করুন বা রেফার করুন।")
            return

        video_data = await video_links_col.find_one({"video_key": args})
        if video_data:
            await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
            sent_video = await bot.send_video(chat_id=uid, video=video_data["file_id"])
            notif_msg = await message.answer("⚠️ **Security Alert:** This video will be deleted in **10 minutes**.")
            
            # ট্রানজেকশন লগ পাঠানো
            await send_log(f"📺 **Video Viewed**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`\n🔑 **Key:** `{args}`\n💰 **Status:** 1 Credit deducted")
            
            asyncio.create_task(auto_delete_video(uid, sent_video.message_id, 600))
            asyncio.create_task(auto_delete_video(uid, notif_msg.message_id, 600))
            return

    await message.answer(f"🎉 Welcome {name}!\n\n💎 **Your starting credits:** 10", reply_markup=get_main_menu())

@dp.message(F.text == "🎁 Claim Free Credit")
async def claim_credit_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    
    if not user:
        await users_col.insert_one({"user_id": uid, "credits": 10, "name": message.from_user.full_name, "joined_at": datetime.utcnow()})
        user = await users_col.find_one({"user_id": uid})

    if user.get("is_banned"):
        return await message.answer("🚫 আপনি নিষিদ্ধ।")

    last_claim = user.get("last_claim_time")
    current_time = datetime.utcnow()

    if last_claim:
        wait_until = last_claim + timedelta(hours=18)
        if current_time < wait_until:
            remaining = wait_until - current_time
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return await message.answer(f"⏳ আপনি ইতিমধ্যে ক্রেডিট নিয়েছেন!\n\nআবার **{hours} ঘণ্টা {minutes} মিনিট** পর চেষ্টা করুন।")

    await users_col.update_one({"user_id": uid}, {"$inc": {"credits": 10}, "$set": {"last_claim_time": current_time}})
    await message.answer("🎉 অভিনন্দন! আপনি সফলভাবে **১০ ক্রেডিট** ক্লেইম করেছেন।\n\nপরবর্তী ক্লেইম ১৮ ঘণ্টা পর করতে পারবেন।")
    
    # ক্লেইম লগ পাঠানো
    await send_log(f"🎁 **Credit Claimed**\n👤 **User:** {message.from_user.full_name}\n🆔 **ID:** `{uid}`\n💰 **Amount:** 10 Credits")

@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    if user and user.get("is_banned"): return await message.answer("🚫 আপনি নিষিদ্ধ।")
    current_credits = user.get("credits", 0) if user else 0
    refer_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    share_text = f"https://t.me/share/url?url={refer_link}&text=বটটি ব্যবহার করে ফ্রি ক্রেডিট পান!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Refer & Earn", url=share_text)],
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    text = (
        f"👤 **User:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {current_credits}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "✨ **Note:** You can earn 10 free credits every time you watch a short ad.\n\n"
        "💰 Don't want to watch ads? Buy credits directly below.\n\n"
        "🎉 Let's keep the fun going!"
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("ban"))
async def ban_user(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id): return
    try:
        target_id = int(command.args)
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": True}}, upsert=True)
        await message.answer(f"✅ User `{target_id}` has been banned.")
        await send_log(f"🚫 **User Banned**\n🆔 **Target ID:** `{target_id}`\n👤 **By Admin:** `{message.from_user.id}`")
    except: await message.answer("❌ Format: `/ban [user_id]`")

@dp.message(Command("unban"))
async def unban_user(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id): return
    try:
        target_id = int(command.args)
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": False}})
        await message.answer(f"✅ User `{target_id}` has been unbanned.")
        await send_log(f"🔓 **User Unbanned**\n🆔 **Target ID:** `{target_id}`\n👤 **By Admin:** `{message.from_user.id}`")
    except: await message.answer("❌ Format: `/unban [user_id]`")

@dp.message(Command("add"))
async def add_credits(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id): return
    try:
        args = command.args.split()
        target_id, amount = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}}, upsert=True)
        await message.answer(f"✅ Added {amount} credits to `{target_id}`")
        await send_log(f"💰 **Manual Credit Added**\n🆔 **To ID:** `{target_id}`\n💵 **Amount:** {amount}\n👤 **By Admin:** `{message.from_user.id}`")
    except: await message.answer("❌ Format: `/add [user_id] [amount]`")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    total_users = await users_col.count_documents({})
    text = f"⚡ **BOT STATUS**\n\n👥 **Total Users:** {total_users}\n💻 **CPU:** {psutil.cpu_percent()}%\n\n`/add [id] [amount]`\n`/ban [id]` | `/unban [id]`"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.video)
async def handle_admin_video(message: types.Message):
    if not is_admin(message.from_user.id): return
    file_id = message.video.file_id
    video_key = f"vid_{str(uuid.uuid4())[:8]}"
    await video_links_col.insert_one({"video_key": video_key, "file_id": file_id, "created_at": datetime.utcnow()})
    await message.answer(f"✅ **Video Saved!**\n🔗 Link: `https://t.me/{BOT_USERNAME}?start={video_key}`", parse_mode="Markdown")

@dp.message()
async def unknown(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    if user and user.get("is_banned"): return
    await message.answer("❓ **Unknown command!**", reply_markup=get_main_menu())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
