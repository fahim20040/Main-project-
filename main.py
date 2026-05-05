import logging
import asyncio
import random
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- ১. কনফিগারেশন ---
API_TOKEN = os.getenv('API_TOKEN', '8565287860:AAGdaKZwgmowMGa1TsnG5zZxyAE9LCyKvRQ')
MONGO_URL = os.getenv('MONGO_URL', "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase")
ADMIN_ID = 6793604200
CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot"

# --- ২. ডাটাবেস ও সার্ভার ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

async def handle(request): return web.Response(text="OK")
async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

# --- ৩. সহায়ক ফাংশন ---
async def is_subscribed(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except: return False

def get_main_kb(uid, user_credits):
    buy_kb = [[InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]]
    return InlineKeyboardMarkup(inline_keyboard=buy_kb)

def get_admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Stats"), KeyboardButton(text="📢 Broadcast")],
        [KeyboardButton(text="➕ Manage Credits")]
    ], resize_keyboard=True)

# --- ৪. মেইন লজিক ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    v_key = command.args
    name = message.from_user.full_name

    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📁 Check Again", callback_data=f"check_{v_key or 'none'}")]
        ])
        await message.answer("⚠️ **You must join all channels to use this bot.**", reply_markup=kb)
        return

    user = await users_col.find_one({"user_id": uid})
    if not user:
        user = {"user_id": uid, "credits": 10, "name": name}
        await users_col.insert_one(user)

    profile_txt = (
        f"👤 **User:** {name}\n"
        f"🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {user['credits']}\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "✨ **Note:** You can earn 10 free credits every time you watch a short ad.\n\n"
        "💸 **Don’t want to watch ads?** You can also buy credits directly from the button below.\n\n"
        "🎉 **Let’s keep the fun going!**"
    )

    r_markup = get_admin_kb() if uid == ADMIN_ID else None
    await message.answer(profile_txt, reply_markup=get_main_kb(uid, user['credits']), parse_mode="Markdown")
    if r_markup: await message.answer("🛠 Admin Panel Active", reply_markup=r_markup)

@dp.callback_query(F.data.startswith("check_"))
async def check_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    v_key = callback.data.split("_")[1]
    
    if await is_subscribed(uid):
        await callback.answer("✅ Thank you for joining all channels.", show_alert=True)
        await callback.message.delete()
        # এখানে চাইলে আপনি পুনরায় স্টার্ট মেসেজটি ট্রিগার করতে পারেন।
    else:
        await callback.answer("❌ You must join all channels to use this bot.", show_alert=True)

# --- ৫. অ্যাডমিন ফিচারস (আপডেটেড ডিজাইন) ---

@dp.message(F.text == "📊 Stats")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    total_users = await users_col.count_documents({})
    total_vids = await video_links_col.count_documents({})
    
    stats_text = (
        "📊 **বট পরিসংখ্যান রিপোর্ট**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **মোট ইউজার:** `{total_users}` জন\n"
        f"🎬 **সংরক্ষিত ভিডিও:** `{total_vids}` টি\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 **সার্ভার স্ট্যাটাস:** `স্থিতিশীল (Stable)`\n"
        "⚡ **বট পারফরম্যান্স:** `১০০% সচল`"
    )
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message(F.text == "📢 Broadcast")
async def admin_broadcast_info(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        "📢 **ব্রডকাস্ট মোড অ্যাক্টিভ!**\n\n"
        "সবাইকে মেসেজ পাঠাতে নিচের ফরম্যাট ব্যবহার করুন:\n"
        "`/broadcast আপনার বার্তাটি এখানে লিখুন`",
        parse_mode="Markdown"
    )

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    
    status_msg = await message.answer("🚀 **ব্রডকাস্ট শুরু হচ্ছে...**")
    users = users_col.find()
    success, failed, total = 0, 0, 0
    
    async for u in users:
        total += 1
        try:
            broadcast_msg = (
                "🔔 **অ্যাডমিন থেকে নতুন বার্তা!**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{command.args}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 @{BOT_USERNAME}"
            )
            await bot.send_message(u['user_id'], broadcast_msg, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            
    report_text = (
        "✅ **ব্রডকাস্ট সম্পন্ন হয়েছে!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 **মোট টার্গেট:** `{total}`\n"
        f"🎉 **সফল হয়েছে:** `{success}`\n"
        f"❌ **ব্যর্থ (ব্লকড):** `{failed}`\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await status_msg.edit_text(report_text, parse_mode="Markdown")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id, amount = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}})
        await message.answer(f"✅ Adjusted `{amount}` credits for ID `{target_id}`")
        try: await bot.send_message(target_id, f"🎁 Admin has adjusted `{amount}` credits in your wallet!")
        except: pass
    except: await message.answer("❌ Format: `/add ID Amount` (Use - for minus)")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
                    
