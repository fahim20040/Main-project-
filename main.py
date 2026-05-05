import logging
import asyncio
import random
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from aiogram.exceptions import TelegramRetryAfter

# --- ১. কনফিগারেশন ---
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = int(os.getenv('ADMIN_ID', '6793604200'))
CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot"

# --- ২. ডাটাবেস ও সার্ভার সেটআপ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

# এন্টি-ফ্লাড মেমোরি
user_last_click = {}

# Cron-job ফিক্স: শুধু ছোট টেক্সট রেসপন্স
async def handle(request): 
    return web.Response(text="OK")

async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

# --- ৩. সহায়ক ফাংশন ---
async def delete_msg(chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try: await bot.delete_message(chat_id, msg_id)
    except: pass

async def is_subscribed(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except: return False

def get_admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 পরিসংখ্যান (Stats)"), KeyboardButton(text="📢 ব্রডকাস্ট মেসেজ")]
    ], resize_keyboard=True)

# --- ৪. মেইন হ্যান্ডলার ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    now = datetime.now()

    # ১. স্প্যাম ফিল্টার: ৩ সেকেন্ডের মধ্যে বারবার ক্লিক করলে ইগনোর করবে
    if uid in user_last_click:
        if (now - user_last_click[uid]).total_seconds() < 3:
            return
    user_last_click[uid] = now

    v_key = command.args
    r_markup = get_admin_keyboard() if uid == ADMIN_ID else None

    # ২. সাবস্ক্রিপশন চেক
    subscribed = await is_subscribed(uid)

    if not subscribed:
        # সাবস্ক্রাইব না করলে ডাটাবেসে সেভ হবে না (Storage বাঁচাবে)
        verify_url = f"https://t.me/{BOT_USERNAME}?start={v_key}" if v_key else f"https://t.me/{BOT_USERNAME}?start=verify"
        join_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 জয়েন চ্যানেল", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ ভেরিফাই (Verify Join)", url=verify_url)]
        ])
        await message.answer("🛑 **অ্যাক্সেস ডিনাইড!**\n\nচ্যানেলে জয়েন করে নিচের 'Verify' বাটনে ক্লিক করুন।", reply_markup=join_kb, parse_mode="Markdown")
        return

    # ৩. ডাটাবেস এন্ট্রি: শুধু ভেরিফাইড ইউজারদের জন্য
    user = await users_col.find_one({"user_id": uid})
    if not user:
        user = {"user_id": uid, "credits": 10, "joined_at": now, "last_active": now}
        await users_col.insert_one(user)
    else:
        await users_col.update_one({"user_id": uid}, {"$set": {"last_active": now}})

    # ৪. রেসপন্স লজিক
    buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])

    if v_key == "verify":
        await message.answer(f"✅ **সফলভাবে ভেরিফাই হয়েছে!**\n\n🆔 আইডি: `{uid}`\n💰 ব্যালেন্স: {user['credits']} ক্রেডিট", reply_markup=r_markup if uid == ADMIN_ID else buy_kb, parse_mode="Markdown")
        return

    if v_key:
        v_data = await video_links_col.find_one({"video_key": v_key})
        if v_data:
            if user['credits'] > 0:
                try:
                    sent_v = await message.answer_video(
                        video=v_data['file_id'],
                        caption=f"🎥 **ভিডিও রেডি!**\n\n💰 অবশিষ্ট ক্রেডিট: {user['credits']-1}\n⚠️ ভিডিওটি ১০ মিনিট পর মুছে যাবে।",
                        reply_markup=buy_kb, parse_mode="Markdown"
                    )
                    await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
                    asyncio.create_task(delete_msg(message.chat.id, sent_v.message_id, 600))
                except Exception as e:
                    logging.error(f"Error: {e}")
            else:
                await message.answer("⚠️ **ক্রেডিট শেষ!**", reply_markup=buy_kb)
        else:
            await message.answer("❌ লিঙ্কটি সঠিক নয়।")
    else:
        await message.answer(f"👋 **স্বাগতম!**\n\n🆔 আইডি: `{uid}`\n💰 ব্যালেন্স: {user['credits']} ক্রেডিট", reply_markup=r_markup if uid == ADMIN_ID else buy_kb, parse_mode="Markdown")

# --- ৫. অ্যাডমিন ও অন্যান্য ---

@dp.message(F.text == "📊 পরিসংখ্যান (Stats)")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total_users = await users_col.count_documents({})
    total_vids = await video_links_col.count_documents({})
    await message.answer(f"📊 **রিপোর্ট**\n\n👥 মোট ইউজার: `{total_users}`\n🎬 মোট ভিডিও: `{total_vids}`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    
    users = users_col.find()
    async for u in users:
        try:
            await bot.send_message(u['user_id'], f"📢 **নোটিশ:**\n\n{command.args}", parse_mode="Markdown")
            await asyncio.sleep(0.05)
        except: pass
    await message.answer("✅ ব্রডকাস্ট সম্পন্ন।")

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def video_handler(message: types.Message):
    v_key = f"vid{random.randint(10000, 99999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    await message.answer(f"✅ লিঙ্ক তৈরি হয়েছে:\n`https://t.me/{BOT_USERNAME}?start={v_key}`", parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
    
