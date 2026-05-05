import logging
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- ১. কনফিগারেশন ---
# আপনার দেওয়া নতুন টোকেনটি এখানে বসানো হয়েছে
API_TOKEN = '8565287860:AAE933txE_spAzMUyhXsoh1yTx6itRu3iKI'
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase"
ADMIN_ID = 6793604200
CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
BOT_USERNAME = "Genz2027bot"

# --- ২. ডাটাবেস ও লগিং ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

# Render Fake Server (Keep-alive)
async def handle(request): return web.Response(text="Bot is Live!")
async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

# --- ৩. কিবোর্ড সেটআপ ---
def get_admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 পরিসংখ্যান (Stats)"), KeyboardButton(text="📢 ব্রডকাস্ট মেসেজ")],
        [KeyboardButton(text="➕ ক্রেডিট ম্যানেজ")]
    ], resize_keyboard=True)

# --- ৪. কমান্ড হ্যান্ডলারস ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    
    if not user:
        user = {"user_id": uid, "credits": 10, "last_active": datetime.now()}
        await users_col.insert_one(user)
    
    text = f"👋 **স্বাগতম!**\n\n🆔 আপনার আইডি: `{uid}`\n💰 ব্যালেন্স: {user['credits']} ক্রেডিট"
    
    # অ্যাডমিন হলে স্পেশাল কিবোর্ড দেখাবে
    kb = get_admin_kb() if uid == ADMIN_ID else None
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# পরিসংখ্যান (Stats) বাটন ফিক্স
@dp.message(F.text == "📊 পরিসংখ্যান (Stats)")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    total = await users_col.count_documents({})
    vids = await video_links_col.count_documents({})
    
    await message.answer(
        f"📊 **বটের রিপোর্ট**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👥 মোট ইউজার: `{total}`\n"
        f"🎬 মোট ভিডিও: `{vids}`\n"
        f"━━━━━━━━━━━━━━", 
        parse_mode="Markdown"
    )

# ব্রডকাস্ট বাটন ফিক্স
@dp.message(F.text == "📢 ব্রডকাস্ট মেসেজ")
async def admin_broadcast_prompt(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📢 মেসেজ পাঠাতে টাইপ করুন:\n`/broadcast আপনার বার্তা`")

@dp.message(Command("broadcast"))
async def process_broadcast(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    
    users = users_col.find()
    success = 0
    async for u in users:
        try:
            await bot.send_message(u['user_id'], f"🔔 **নোটিশ:**\n\n{command.args}")
            success += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ ব্রডকাস্ট সম্পন্ন! {success} জন ইউজার মেসেজ পেয়েছে।")

# --- ৫. মেইন রানার (Conflict সমাধান) ---
async def main():
    # সেশন ক্লিয়ার করা যাতে Conflict Error না আসে
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
    
