import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from motor.motor_asyncio import AsyncIOMotorClient

# ১. কনফিগারেশন
API_TOKEN = '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ'
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase"
ADMIN_ID = 6793604200 
ADMIN_LINK = "t.me/artist_x0"

# ২. লগিং এবং বট সেটআপ
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']

# ৩. ইউজার তথ্য ম্যানেজমেন্ট
async def get_user(user_id):
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "credits": 10}
        await users_col.insert_one(user)
    return user

# ৪. স্টার্ট কমান্ড (Deep Linking হ্যান্ডলিং সহ)
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user = await get_user(message.from_user.id)
    args = message.text.split(maxsplit=1)
    
    if len(args) > 1:
        video_id = args[1]
        
        if user['credits'] > 0:
            new_credits = user['credits'] - 1
            await users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"credits": -1}})
            
            try:
                await message.answer_video(
                    video=video_id, 
                    caption=f"✅ আপনার ভিডিও প্রস্তুত!\n💰 অবশিষ্ট ক্রেডিট: {new_credits}"
                )
            except Exception as e:
                await message.answer(f"❌ ভিডিও পাঠাতে সমস্যা হয়েছে: {e}")
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 ক্রেডিট কিনুন", url=f"https://{ADMIN_LINK}")]
            ])
            await message.answer("⚠️ আপনার ক্রেডিট শেষ! আরও ভিডিও দেখতে ক্রেডিট কিনুন।", reply_markup=keyboard)
    else:
        await message.answer(f"👋 স্বাগতম!\nআপনার বর্তমান ক্রেডিট: {user['credits']}\n\nভিডিও পেতে লিঙ্কে ক্লিক করুন।")

# ৫. প্রোফাইল বা ক্রেডিট চেক কমান্ড
@dp.message(Command("credits"))
async def check_credits(message: types.Message):
    user = await get_user(message.from_user.id)
    await message.answer(f"👤 আপনার প্রোফাইল:\n💰 বর্তমান ক্রেডিট: {user['credits']}")

# ৬. ব্রডকাস্টিং (শুধুমাত্র অ্যাডমিনের জন্য)
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast ", "")
    if not text or text == "/broadcast":
        await message.answer("⚠️ সঠিক ফরম্যাট: `/broadcast আপনার মেসেজ`", parse_mode="Markdown")
        return

    all_users = users_col.find()
    count = 0
    async for user in all_users:
        try:
            await bot.send_message(user['user_id'], text)
            count += 1
        except Exception as e:
            logging.error(f"Error sending to {user['user_id']}: {e}")
    
    await message.answer(f"📢 মোট {count} জন ইউজারকে মেসেজ পাঠানো হয়েছে।")

# ৭. অ্যাডমিনের জন্য ভিডিও আইডি পাওয়া
@dp.message(lambda message: message.video)
async def get_video_id(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"🎬 ভিডিও ফাইল আইডি:\n`{message.video.file_id}`", parse_mode="Markdown")

# ৮. বট রান করা
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
        
