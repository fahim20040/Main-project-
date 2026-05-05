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

    # চ্যানেল জয়েন চেক
    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📁 Check Again", callback_data=f"check_{v_key or 'none'}")]
        ])
        await message.answer("⚠️ **You must join all channels to use this bot.**", reply_markup=kb)
        return

    # ডাটাবেস আপডেট
    user = await users_col.find_one({"user_id": uid})
    if not user:
        user = {"user_id": uid, "credits": 10, "name": name}
        await users_col.insert_one(user)

    # প্রফেশনাল ইউজার ইন্টারফেস (আপনার দেওয়া ডিজাইন অনুযায়ী)
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

# পপ-আপ অ্যালার্ট হ্যান্ডলার
@dp.callback_query(F.data.startswith("check_"))
async def check_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    v_key = callback.data.split("_")[1]
    
    if await is_subscribed(uid):
        await callback.answer("✅ Thank you for joining all channels.", show_alert=True)
        # জয়েন করার পর মেইন স্টার্ট ফাংশন ট্রিগার করবে
        await callback.message.delete()
        # এখানে রি-ডাইরেক্ট কোড...
    else:
        await callback.answer("❌ You must join all channels to use this bot.", show_alert=True)

# --- ৫. অ্যাডমিন ফিচারস ---

@dp.message(F.text == "📊 Stats")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total = await users_col.count_documents({})
    await message.answer(f"📊 **Bot Statistics**\n\n👥 Total Users: `{total}`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    status = await message.answer("⏳ Sending messages...")
    users = users_col.find()
    s, f = 0, 0
    async for u in users:
        try:
            await bot.send_message(u['user_id'], f"📢 **Admin Notice:**\n\n{command.args}")
            s += 1
            await asyncio.sleep(0.05)
        except: f += 1
    await status.edit_text(f"✅ Broadcast Done!\n🚀 Success: {s}\n❌ Failed: {f}")

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

