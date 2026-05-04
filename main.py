import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from motor.motor_asyncio import AsyncIOMotorClient

# কনফিগারেশন
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'
MONGO_URL = "YOUR_MONGODB_URL_HERE"
ADMIN_ID = 123456789  # আপনার টেলিগ্রাম আইডি

# লগিং এবং বট সেটআপ
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']

# ১. ইউজার জয়েন করলে ১০ ক্রেডিট ফ্রি
async def get_user(user_id):
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "credits": 10}
        await users_col.insert_one(user)
    return user

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    # Deep Linking চেক করা (start=video_123)
    args = message.text.split()
    user = await get_user(message.from_user.id)
    
    if len(args) > 1:
        video_id = args[1]
        
        # ২. ক্রেডিট চেক
        if user['credits'] > 0:
            # এখানে ভিডিও সেন্ড করার লজিক (আপনার ডাটাবেজ থেকে video_id অনুযায়ী)
            await users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"credits": -1}})
            await message.answer_video(video=video_id, caption=f"আপনার ভিডিও! বাকি ক্রেডিট: {user['credits']-1}")
        else:
            # ক্রেডিট শেষ হয়ে গেলে কাস্টম বাটনসহ মেসেজ
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="ক্রেডিট কিনুন", url="https://t.me/your_admin_link")],
                [InlineKeyboardButton(text="ফ্রি ক্রেডিট পান", callback_data="free_tasks")]
            ])
            await message.answer("আপনার ক্রেডিট শেষ! ভিডিও দেখতে ক্রেডিট সংগ্রহ করুন।", reply_markup=keyboard)
    else:
        await message.answer(f"স্বাগতম! আপনার বর্তমান ক্রেডিট: {user['credits']}")

# ৩. প্রমোশনাল মেসেজ (Broadcasting)
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    text = message.text.replace("/broadcast ", "")
    all_users = users_col.find()
    count = 0
    async for user in all_users:
        try:
            await bot.send_message(user['user_id'], text)
            count += 1
        except: pass
    await message.answer(f"মোট {count} জন ইউজারকে মেসেজ পাঠানো হয়েছে।")

# ভিডিও ফাইল আইডি পাওয়ার জন্য (শুধু এডমিন ব্যবহার করবে)
@dp.message(lambda message: message.video)
async def get_video_id(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"এই ভিডিওর ID: `{message.video.file_id}`\n\nলিংক হবে: `https://t.me/YOUR_BOT_USERNAME?start={message.video.file_id}`", parse_mode="Markdown")

if __name__ == "__main__":
    dp.run_polling(bot)
  
