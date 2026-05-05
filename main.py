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

# --- ১. কনফিগারেশন ---
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = int(os.getenv('ADMIN_ID', '6793604200'))
CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0" # ক্রেডিট কেনার জন্য আপনার আইডি

# --- ২. ডাটাবেস ও সার্ভার সেটআপ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

async def handle(request): return web.Response(text="Bot is running!")
async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 10000)))
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

# --- ৪. অ্যাডমিন কিবোর্ড (সব সময় নিচে থাকবে) ---
def get_admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 পরিসংখ্যান (Stats)"), KeyboardButton(text="📢 ব্রডকাস্ট মেসেজ")]
    ], resize_keyboard=True)

# --- ৫. কমান্ড হ্যান্ডলারস ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    user = await get_user(uid)
    v_key = command.args
    
    # অ্যাডমিন হলে স্পেশাল মেনু পাবে
    r_markup = get_admin_keyboard() if uid == ADMIN_ID else None

    # মেম্বারশিপ চেক (কড়াকড়ি)
    if not await is_subscribed(uid):
        verify_url = f"https://t.me/Genz2027bot?start={v_key}" if v_key else "https://t.me/Genz2027bot?start"
        join_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 জয়েন চ্যানেল", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ ভেরিফাই (Verify Join)", url=verify_url)]
        ])
        await message.answer("🛑 **অ্যাক্সেস ডিনাইড!**\n\nবটটি ব্যবহার করতে আপনাকে অবশ্যই আমাদের চ্যানেলে জয়েন থাকতে হবে। জয়েন করে নিচের 'Verify' বাটনে ক্লিক করুন।", reply_markup=join_kb, parse_mode="Markdown")
        return

    # ভিডিও কি থাকলে
    if v_key:
        v_data = await video_links_col.find_one({"video_key": v_key})
        if v_data:
            if user['credits'] > 0:
                buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
                sent_v = await message.answer_video(
                    video=v_data['file_id'],
                    caption=f"🎥 **ভিডিওটি রেডি!**\n\n🆔 আইডি: `{uid}`\n💰 অবশিষ্ট ক্রেডিট: {user['credits']-1}\n⚠️ ভিডিওটি ১০ মিনিট পর মুছে যাবে।",
                    reply_markup=buy_kb, parse_mode="Markdown"
                )
                await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
                asyncio.create_task(delete_msg(message.chat.id, sent_v.message_id, 600))
            else:
                buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
                await message.answer("⚠️ **ক্রেডিট শেষ!**\n\nআপনার ব্যালেন্স ০। ক্রেডিট কিনতে নিচের বাটনে ক্লিক করুন।", reply_markup=buy_kb)
        else:
            await message.answer("❌ দুঃখিত, এই ভিডিও লিঙ্কটি কাজ করছে না।")
    else:
        # মেইন মেনু
        buy_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 ক্রেডিট কিনুন", url=f"https://t.me/{ADMIN_USERNAME}")]])
        await message.answer(f"👋 **স্বাগতম!**\n\n🆔 আপনার আইডি: `{uid}`\n💰 বর্তমান ব্যালেন্স: {user['credits']} ক্রেডিট", reply_markup=r_markup if uid == ADMIN_ID else buy_kb, parse_mode="Markdown")

# --- ৬. অ্যাডমিন ফাংশনালিটি ---

@dp.message(F.text == "📊 পরিসংখ্যান (Stats)")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total_users = await users_col.count_documents({})
    active_24h = await users_col.count_documents({"last_active": {"$gte": datetime.now() - timedelta(days=1)}})
    total_vids = await video_links_col.count_documents({})
    await message.answer(f"📊 **বটের রিপোর্ট**\n\n👥 টোটাল ইউজার: `{total_users}`\n🔥 এক্টিভ (২৪ঘণ্টা): `{active_24h}`\n🎬 মোট ভিডিও: `{total_vids}`", parse_mode="Markdown")

@dp.message(F.text == "📢 ব্রডকাস্ট মেসেজ")
async def broadcast_info(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📢 সবাইকে মেসেজ পাঠাতে লিখুন:\n`/broadcast আপনার মেসেজ`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    if not command.args: return await message.answer("❌ মেসেজ লিখুন।")
    users = users_col.find()
    count = 0
    async for u in users:
        try:
            await bot.send_message(u['user_id'], f"📢 **অ্যাডমিন নোটিশ:**\n\n{command.args}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ `{count}` জন ইউজারকে মেসেজ পাঠানো হয়েছে।")

@dp.message(Command("add"))
async def add_credit(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        await users_col.update_one({"user_id": int(args[0])}, {"$inc": {"credits": int(args[1])}})
        await message.answer(f"✅ ইউজার `{args[0]}` কে {args[1]} ক্রেডিট দেওয়া হয়েছে।")
    except: await message.answer("❌ ফরম্যাট: `/add ID Amount`")

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def video_handler(message: types.Message):
    v_key = f"vid{random.randint(10000, 99999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    await message.answer(f"✅ লিঙ্ক তৈরি হয়েছে:\n`https://t.me/Genz2027bot?start={v_key}`", parse_mode="Markdown")

# ৭ দিন পরপর রিমাইন্ডার পাঠানোর অটো টাস্ক
async def reminder_task():
    while True:
        await asyncio.sleep(86400 * 7)
        async for u in users_col.find():
            if not await is_subscribed(u['user_id']):
                try: await bot.send_message(u['user_id'], "🔔 আপনি আমাদের চ্যানেল থেকে বের হয়ে গেছেন। নতুন ভিডিও পেতে আবার জয়েন করুন!")
                except: pass

async def main():
    asyncio.create_task(reminder_task())
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
                                    
