import logging
import asyncio
import random
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- ১. কনফিগারেশন (Environment Variables) ---
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = int(os.getenv('ADMIN_ID', '6793604200'))

CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl" 

# --- ২. পোর্ট এরর ফিক্স করার জন্য ফেক সার্ভার ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 10000)))
    await site.start()

# --- ৩. বট সেটআপ ---
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

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user_data(user_id)
    video_key = command.args 

    if not await is_user_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 জয়েন চ্যানেল", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ চেক জয়েন", url=f"https://t.me/Genz2027bot?start={video_key}" if video_key else "https://t.me/Genz2027bot?start")]
        ])
        await message.answer("🛑 ভিডিও পেতে জয়েন করা বাধ্যতামূলক!", reply_markup=keyboard)
        return

    if video_key:
        video_data = await video_links_col.find_one({"video_key": video_key})
        if video_data:
            if user['credits'] > 0:
                sent_v = await message.answer_video(video=video_data['file_id'], caption=f"💰 ক্রেডিট: {user['credits'] - 1}")
                await users_col.update_one({"user_id": user_id}, {"$inc": {"credits": -1}})
                await asyncio.sleep(600)
                try: await bot.delete_message(message.chat.id, sent_v.message_id)
                except: pass
            else:
                await message.answer("⚠️ আপনার কোনো ক্রেডিট নেই!")
    else:
        await message.answer(f"👋 স্বাগতম!\n💰 আপনার ক্রেডিট: {user['credits']}")

@dp.message(lambda m: m.video and m.from_user.id == ADMIN_ID)
async def video_handler(message: types.Message):
    v_key = f"vid{random.randint(1000, 9999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    await message.answer(f"✅ ভিডিওর লিঙ্ক তৈরি হয়েছে:\n`https://t.me/Genz2027bot?start={v_key}`", parse_mode="Markdown")

async def main():
    await start_fake_server() # এটি Render-এর পোর্ট এরর দূর করবে
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
