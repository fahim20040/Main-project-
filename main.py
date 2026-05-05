import logging
import asyncio
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- ১. কনফিগারেশন (আপনার নতুন টোকেন যুক্ত করা হয়েছে) ---
API_TOKEN = '8565287860:AAE933txE_spAzMUyhXsoh1yTx6itRu3iKI'
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:j3XwaF5yZmbfPbYQ@mybotdatabase.5m5engl.mongodb.net/?appName=MyBotDatabase"
ADMIN_ID = 6793604200
CHANNEL_ID = -1003960638119 
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot"

# --- ২. ডাটাবেস ও সার্ভার সেটআপ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client['video_bot_db']
users_col = db['users']
video_links_col = db['video_links']

# Render Keep-Alive Server
async def handle(request): return web.Response(text="Bot is running!")
async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

# --- ৩. সহায়ক ফাংশন ও কিবোর্ড ---
async def is_subscribed(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except: return False

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])

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
        "✨ **Note:** You can earn 10 free credits by watching ads.\n"
        "🎉 **Enjoy your time!**"
    )

    r_markup = get_admin_kb() if uid == ADMIN_ID else None
    await message.answer(profile_txt, reply_markup=get_main_kb(), parse_mode="Markdown")
    if r_markup: await message.answer("🛠 Admin Panel Active", reply_markup=r_markup)

@dp.callback_query(F.data.startswith("check_"))
async def check_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.answer("✅ Subscribed!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("❌ Please join the channel first!", show_alert=True)

# --- ৫. অ্যাডমিন ফিচারস (Stats & Broadcast ফিক্স) ---

@dp.message(F.text == "📊 Stats")
async def admin_stats_fixed(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    total_users = await users_col.count_documents({})
    total_vids = await video_links_col.count_documents({})
    
    report = (
        "📊 **System Status Report**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🎬 **Stored Videos:** `{total_vids}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 **Server:** `Online` | ⚡ **Ping:** `Stable`"
    )
    await message.answer(report, parse_mode="Markdown")

@dp.message(F.text == "📢 Broadcast")
async def admin_broadcast_fixed(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        "📢 **Broadcast Mode Active**\n\n"
        "To send a message to everyone, use:\n"
        "`/send Your Message Here`",
        parse_mode="Markdown"
    )

@dp.message(Command("send"))
async def process_send(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    
    status = await message.answer("⏳ Sending...")
    users = users_col.find()
    s, f = 0, 0
    
    async for u in users:
        try:
            # ইউনিক ডিজাইনড মেসেজ
            msg = (
                "📢 **New Announcement**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{command.args}\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await bot.send_message(u['user_id'], msg, parse_mode="Markdown")
            s += 1
            await asyncio.sleep(0.05)
        except:
            f += 1
            
    await status.edit_text(f"✅ **Sent!**\n🚀 Success: `{s}`\n❌ Failed: `{f}`")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id, amount = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}})
        await message.answer(f"✅ ID `{target_id}` added `{amount}` credits.")
    except:
        await message.answer("❌ Format: `/add ID Amount`")

# --- ৬. রানার (Conflict ফিক্সড) ---
async def main():
    # সেশন ক্লিয়ারেন্স
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
    
