import logging
import asyncio
import random
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- ১. কনফিগারেশন ---
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = int(os.getenv('ADMIN_ID', '6793604200'))

CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl" 

# --- ২. Render পোর্ট এরর ফিক্স ---
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

# --- ৩. ভিডিও অটো-ডিলিট লজিক ---
async def delete_message_after_time(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except: pass

# --- ৪. সেটআপ ---
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

# --- ৫. কমান্ড হ্যান্ডলারস ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user_data(user_id)
    video_key = command.args 

    # সাবস্ক্রিপশন চেক
    subscribed = await is_user_subscribed(user_id)
    
    if not subscribed:
        # ভেরিফাই বাটন ঠিক করা হয়েছে
        check_url = f"https://t.me/Genz2027bot?start={video_key}" if video_key else "https://t.me/Genz2027bot?start"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 জয়েন চ্যানেল", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ জয়েন করেছি (Verify)", url=check_url)]
        ])
        await message.answer("🛑 **চ্যানেলে জয়েন করা বাধ্যতামূলক!**\n\nভিডিওটি পেতে নিচের বাটনে ক্লিক করে জয়েন করুন এবং 'Verify' বাটনে ক্লিক করুন।", reply_markup=kb, parse_mode="Markdown")
        return

    # জয়েন থাকলে ভিডিও প্রসেস
    if video_key:
        v_data = await video_links_col.find_one({"video_key": video_key})
        if v_data and user['credits'] > 0:
            sent_v = await message.answer_video(
                video=v_data['file_id'], 
                caption=f"💰 অবশিষ্ট ক্রেডিট: {user['credits'] - 1}\n🆔 আপনার আইডি: `{user_id}`\n⚠️ ১০ মিনিট পর ভিডিওটি মুছে যাবে।",
                parse_mode="Markdown"
            )
            await users_col.update_one({"user_id": user_id}, {"$inc": {"credits": -1}})
            asyncio.create_task(delete_message_after_time(message.chat.id, sent_v.message_id, 600))
        else:
            await message.answer("⚠️ ক্রেডিট নেই বা ভিডিওটি পাওয়া যায়নি।")
    else:
        # প্রথম মেসেজেই আইডি শো করবে
        await message.answer(f"👋 স্বাগতম!\n🆔 আপনার আইডি: `{user_id}`\n💰 বর্তমান ক্রেডিট: {user['credits']}", parse_mode="Markdown")

@dp.message(Command("add"))
async def add_credit(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id, amount = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}})
        await message.answer(f"✅ ইউজার `{target_id}` কে {amount} ক্রেডিট দেওয়া হয়েছে।")
    except:
        await message.answer("❌ ফরম্যাট: `/add ID Amount`")

@dp.message(lambda m: m.video and m.from_user.id == ADMIN_ID)
async def video_handler(message: types.Message):
    v_key = f"vid{random.randint(1000, 9999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    await message.answer(f"✅ লিঙ্ক তৈরি হয়েছে:\n`https://t.me/Genz2027bot?start={v_key}`", parse_mode="Markdown")

async def main():
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
        
