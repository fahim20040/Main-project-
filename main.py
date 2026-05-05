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

# --- ১. কনফিগারেশন ---
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
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]])

def get_admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Stats"), KeyboardButton(text="📢 Broadcast")],
        [KeyboardButton(text="➕ Manage Credits")]
    ], resize_keyboard=True)

# অটো ডিলিট ফাংশন
async def auto_delete(chat_id, msg_id):
    await asyncio.sleep(600) # ১০ মিনিট
    try: await bot.delete_message(chat_id, msg_id)
    except: pass

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

    if v_key:
        v_data = await video_links_col.find_one({"video_key": v_key})
        if v_data:
            if user['credits'] > 0:
                # এখানে আপনার দেওয়া ওয়ার্নিং মেসেজটি যোগ করা হয়েছে
                sent_v = await message.answer_video(
                    video=v_data['file_id'], 
                    caption=f"🎬 **ভিডিও রেডি!**\n💰 আপনার ক্রেডিট: {user['credits'] - 1}\n\nwarning ⚠️ভিডিও টি,১০ মিনিট পড়ে ডিলিট হয়ে যাবে"
                )
                await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
                asyncio.create_task(auto_delete(message.chat.id, sent_v.message_id))
                return
            else:
                await message.answer("⚠️ আপনার পর্যাপ্ত ক্রেডিট নেই!")
                return

    profile_txt = (
        f"👤 **User:** {name}\n🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {user['credits']}\n\n"
        "✨ Earn free credits by watching ads.\n🎉 Enjoy your time!"
    )
    r_markup = get_admin_kb() if uid == ADMIN_ID else None
    await message.answer(profile_txt, reply_markup=get_main_kb(), parse_mode="Markdown")
    if r_markup: await message.answer("🛠 Admin Panel Active", reply_markup=r_markup)

# অ্যাডমিন ভিডিও আপলোড
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def admin_video_upload(message: types.Message):
    v_key = f"vid{random.randint(1000, 9999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    link = f"https://t.me/{BOT_USERNAME}?start={v_key}"
    await message.answer(f"✅ **ভিডিও সেভ হয়েছে!**\n\n🔗 লিঙ্ক:\n`{link}`", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_"))
async def check_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.answer("✅ Subscribed!", show_alert=True)
        await callback.message.delete()
    else: await callback.answer("❌ Please join first!", show_alert=True)

# --- ৫. অ্যাডমিন ফিচারস ---

@dp.message(F.text == "📊 Stats")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total_u = await users_col.count_documents({})
    total_v = await video_links_col.count_documents({})
    report = f"📊 **System Status**\n━━━━━━━━━━━━━\n👥 ইউজার: `{total_u}`\n🎬 ভিডিও: `{total_v}`\n━━━━━━━━━━━━━"
    await message.answer(report, parse_mode="Markdown")

@dp.message(F.text == "📢 Broadcast")
async def admin_broadcast_prompt(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📢 **ব্রডকাস্ট:**\n`/send আপনার মেসেজ`", parse_mode="Markdown")

@dp.message(Command("send"))
async def process_send(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID or not command.args: return
    status = await message.answer("⏳ Sending...")
    users = users_col.find(); s, f = 0, 0
    async for u in users:
        try:
            await bot.send_message(u['user_id'], f"📢 **New Announcement**\n━━━━━━━━━━━━━\n\n{command.args}\n\n━━━━━━━━━━━━━", parse_mode="Markdown")
            s += 1; await asyncio.sleep(0.05)
        except: f += 1
    await status.edit_text(f"✅ **Sent!**\n🚀 সফল: `{s}`\n❌ ব্যর্থ: `{f}`")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split(); target_id, amt = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amt}})
        await message.answer(f"✅ ID `{target_id}` added `{amt}` credits.")
    except: await message.answer("❌ `/add ID Amount`")

# --- ৬. রানার ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
    
