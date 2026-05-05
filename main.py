import logging
import asyncio
import random
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- ১. কনফিগারেশন (Environment Variables) ---
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = int(os.getenv('ADMIN_ID', '6793604200'))

CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl" 

# --- ২. Render-এর পোর্ট এরর ফিক্স (Fake Server) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- ৩. সেটআপ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

async def is_user_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

async def get_user_data(user_id):
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "credits": 10, "last_refill": datetime.now()}
        await users_col.insert_one(user)
    return user

# --- ৪. কমান্ড হ্যান্ডলারস ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user_data(user_id)
    video_key = command.args 

    if not await is_user_subscribed(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 জয়েন চ্যানেল", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ চেক জয়েন", url=f"https://t.me/Genz2027bot?start={video_key}" if video_key else "https://t.me/Genz2027bot?start")]
        ])
        await message.answer("🛑 ভিডিও পেতে জয়েন করা বাধ্যতামূলক!", reply_markup=kb)
        return

    if video_key:
        v_data = await video_links_col.find_one({"video_key": video_key})
        if v_data:
            if user['credits'] > 0:
                sent_v = await message.answer_video(video=v_data['file_id'], caption=f"💰 আপনার অবশিষ্ট ক্রেডিট: {user['credits'] - 1}")
                await users_col.update_one({"user_id": user_id}, {"$inc": {"credits": -1}})
                # ১০ মিনিট পর ভিডিও ডিলিট (Auto Delete)
                async def delete_msg(m):
                    await asyncio.sleep(600)
                    try: await bot.delete_message(m.chat.id, m.message_id)
                    except: pass
                asyncio.create_task(delete_msg(sent_v))
            else:
                await message.answer("⚠️ আপনার ক্রেডিট শেষ!")
    else:
        await message.answer(f"👋 স্বাগতম!\n💰 আপনার বর্তমান ক্রেডিট: {user['credits']}")

@dp.message(Command("add"))
async def add_credit(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id = int(args[0])
        amount = int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}})
        await message.answer(f"✅ ইউজার `{target_id}` কে {amount} ক্রেডিট দেওয়া হয়েছে।")
        await bot.send_message(target_id, f"🎁 অ্যাডমিন আপনাকে {amount} ক্রেডিট পাঠিয়েছেন।")
    except:
        await message.answer("❌ ফরম্যাট: `/add ID Amount`")

@dp.message(lambda m: m.video and m.from_user.id == ADMIN_ID)
async def video_handler(message: types.Message):
    v_key = f"vid{random.randint(1000, 9999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    await message.answer(f"✅ লিঙ্ক তৈরি হয়েছে:\n`https://t.me/Genz2027bot?start={v_key}`", parse_mode="Markdown")

# --- ৫. রান করা ---
async def main():
    await asyncio.gather(
        start_fake_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
            
