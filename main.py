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
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError

# --- ১. কনফিগারেশন ---
# সিকিউরিটির জন্য সরাসরি টোকেন না লিখে Environment Variable ব্যবহার করা ভালো
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = int(os.getenv('ADMIN_ID', '6793604200'))
CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot" # আপনার বটের ইউজারনেম

# --- ২. ডাটাবেস ও সার্ভার সেটআপ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

# এন্টি-ফ্লাড ডিকশনারি
user_last_request = {}

# Render-এর জন্য Keep-Alive সার্ভার (Cron-job এখানে হিট করবে)
async def handle(request): 
    return web.Response(text="Bot is awake and running!")

async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render নিজে থেকে পোর্ট অ্যাসাইন করে, তাই ডিফল্ট 8080 রাখা হলো
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
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

async def get_user(user_id):
    u = await users_col.find_one({"user_id": user_id})
    if not u:
        u = {"user_id": user_id, "credits": 10, "joined_at": datetime.now(), "last_active": datetime.now()}
        await users_col.insert_one(u)
    else:
        await users_col.update_one({"user_id": user_id}, {"$set": {"last_active": datetime.now()}})
    return u

def get_admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 পরিসংখ্যান (Stats)"), KeyboardButton(text="📢 ব্রডকাস্ট মেসেজ")]
    ], resize_keyboard=True)

# --- ৪. কমান্ড হ্যান্ডলারস ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    
    # ভিডিও রিকোয়েস্ট স্প্যাম প্রতিরোধ (৫ সেকেন্ড গ্যাপ)
    now = datetime.now()
    if uid in user_last_request:
        if (now - user_last_request[uid]).total_seconds() < 5:
            return 
    user_last_request[uid] = now

    user = await get_user(uid)
    v_key = command.args
    r_markup = get_admin_keyboard() if uid == ADMIN_ID else None

    # চ্যানেল সাবস্ক্রিপশন চেক ও ভেরিফাই বাটন ফিক্স
    if not await is_subscribed(uid):
        verify_url = f"https://t.me/{BOT_USERNAME}?start={v_key}" if v_key else f"https://t.me/{BOT_USERNAME}?start=verify"
        join_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 জয়েন চ্যানেল", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ ভেরিফাই (Verify Join)", url=verify_url)]
        ])
        await message.answer("🛑 **অ্যাক্সেস ডিনাইড!**\n\nচ্যানেলে জয়েন করে নিচের 'Verify' বাটনে ক্লিক করুন।", reply_markup=join_kb, parse_mode="Markdown")
        return

    # ভেরিফাই সাকসেস মেসেজ
    if v_key == "verify":
        buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
        await message.answer(f"✅ **ভেরিফিকেশন সফল হয়েছে!**\n\n👋 **স্বাগতম!**\n\n🆔 আপনার আইডি: `{uid}`\n💰 ব্যালেন্স: {user['credits']} ক্রেডিট", reply_markup=r_markup if uid == ADMIN_ID else buy_kb, parse_mode="Markdown")
        return

    # ভিডিও পাঠানো লজিক
    if v_key:
        v_data = await video_links_col.find_one({"video_key": v_key})
        if v_data:
            if user['credits'] > 0:
                buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
                try:
                    sent_v = await message.answer_video(
                        video=v_data['file_id'],
                        caption=f"🎥 **ভিডিওটি রেডি!**\n\n🆔 আইডি: `{uid}`\n💰 অবশিষ্ট ক্রেডিট: {user['credits']-1}\n⚠️ ভিডিওটি ১০ মিনিট পর মুছে যাবে।",
                        reply_markup=buy_kb, parse_mode="Markdown"
                    )
                    await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
                    asyncio.create_task(delete_msg(message.chat.id, sent_v.message_id, 600))
                except Exception as e:
                    logging.error(f"Send video error: {e}")
            else:
                buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
                await message.answer("⚠️ **আপনার ক্রেডিট শেষ!**", reply_markup=buy_kb)
        else:
            await message.answer("❌ লিঙ্কটি ভুল বা মেয়াদ শেষ।")
    else:
        # নরমাল স্টার্ট কমান্ড
        buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
        await message.answer(f"👋 **স্বাগতম!**\n\n🆔 আপনার আইডি: `{uid}`\n💰 বর্তমান ব্যালেন্স: {user['credits']} ক্রেডিট", reply_markup=r_markup if uid == ADMIN_ID else buy_kb, parse_mode="Markdown")

# --- ৫. অ্যাডমিন ফাংশনালিটি ---

@dp.message(F.text == "📊 পরিসংখ্যান (Stats)")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total_users = await users_col.count_documents({})
    active_24h = await users_col.count_documents({"last_active": {"$gte": datetime.now() - timedelta(days=1)}})
    total_vids = await video_links_col.count_documents({})
    await message.answer(f"📊 **বটের রিপোর্ট**\n\n👥 মোট ইউজার: `{total_users}`\n🔥 গত ২৪ ঘণ্টায় এক্টিভ: `{active_24h}`\n🎬 মোট ভিডিও: `{total_vids}`", parse_mode="Markdown")

@dp.message(F.text == "📢 ব্রডকাস্ট মেসেজ")
async def broadcast_info(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📢 সবাইকে মেসেজ পাঠাতে নিচের মতো করে লিখুন:\n`/broadcast আপনার মেসেজ`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    if not command.args: return await message.answer("❌ মেসেজ লিখুন।")
    
    status_msg = await message.answer("⏳ ব্রডকাস্ট শুরু হয়েছে...")
    users = users_col.find()
    count = 0
    async for u in users:
        try:
            await bot.send_message(u['user_id'], f"📢 **অ্যাডমিন নোটিশ:**\n\n{command.args}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except: pass
            
    await status_msg.edit_text(f"✅ সফলভাবে `{count}` জন ইউজারকে মেসেজ পাঠানো হয়েছে।")

@dp.message(Command("add"))
async def add_credit(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        await users_col.update_one({"user_id": int(args[0])}, {"$inc": {"credits": int(args[1])}})
        await message.answer(f"✅ ইউজার `{args[0]}` কে {args[1]} ক্রেডিট দেওয়া হয়েছে।")
    except: await message.answer("❌ ফরম্যাট ভুল। সঠিক নিয়ম: `/add ID Amount`")

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def video_handler(message: types.Message):
    v_key = f"vid{random.randint(10000, 99999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    await message.answer(f"✅ ভিডিওর লিঙ্ক তৈরি হয়েছে:\n`https://t.me/{BOT_USERNAME}?start={v_key}`", parse_mode="Markdown")

async def reminder_task():
    while True:
        await asyncio.sleep(86400 * 7) # প্রতি ৭ দিন পর পর চেক করবে
        async for u in users_col.find():
            if not await is_subscribed(u['user_id']):
                try: 
                    await bot.send_message(u['user_id'], "🔔 আপনি আমাদের চ্যানেল থেকে বের হয়ে গেছেন। নতুন ভিডিও পেতে আবার জয়েন করুন!")
                    await asyncio.sleep(0.05)
                except: pass

async def main():
    asyncio.create_task(reminder_task())
    await bot.delete_webhook(drop_pending_updates=True)
    # fake_server এবং bot polling একসাথে চলবে
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
    
