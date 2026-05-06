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

# মেইন মেনু (Reply Keyboard)
def get_main_menu():
    kb = [
        [KeyboardButton(text="Start the bot"), KeyboardButton(text="Check your wallet")],
        [KeyboardButton(text="Buy credits"), KeyboardButton(text="Get channels")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# রেফারেল লিংক জেনারেটর
def get_refer_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

# অটো ডিলিট ফাংশন
async def auto_delete(chat_id, msg_id):
    await asyncio.sleep(300) # ৫ মিনিট (আপনার স্ক্রিনশট অনুযায়ী)
    try: await bot.delete_message(chat_id, msg_id)
    except: pass

# --- ৪. মেইন লজিক ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    args = command.args
    name = message.from_user.full_name

    # ১. চ্যানেল সাবস্ক্রিপশন চেক
    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📁 Check Again", callback_data=f"check_{args or 'none'}")]
        ])
        await message.answer("⚠️ **You must join all channels to use this bot.**", reply_markup=kb)
        return

    # ইউজার ডাটাবেসে আছে কি না দেখা এবং রেফারেল প্রসেস
    user = await users_col.find_one({"user_id": uid})
    if not user:
        # যদি কেউ রেফার করে থাকে
        if args and args.startswith("ref_"):
            referrer_id = int(args.split("_")[1])
            if referrer_id != uid:
                await users_col.update_one({"user_id": referrer_id}, {"$inc": {"credits": 5}})
                try:
                    await bot.send_message(referrer_id, "🎉 Someone joined using your link! You got 5 credits.")
                except: pass

        user = {"user_id": uid, "credits": 10, "name": name}
        await users_col.insert_one(user)
    
    # স্ক্রিনশট ১ অনুযায়ী: চ্যানেল জয়েন শেষে ধন্যবাদ মেসেজ
    if args and args.startswith("none"): # সাবস্ক্রিপশন চেকের পর আসলে
        await message.answer("thank you for joining all channels.")

    # যদি ভিডিও কি (Key) থাকে
    if args and not args.startswith("ref_") and args != "none":
        v_data = await video_links_col.find_one({"video_key": args})
        if v_data:
            if user['credits'] > 0:
                sent_v = await message.answer_video(
                    video=v_data['file_id'], 
                    caption="⌛ Sent file(s) will be automatically deleted after 5 minutes due to Telegram copyright issues."
                )
                await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
                asyncio.create_task(auto_delete(message.chat.id, sent_v.message_id))
                return
            else:
                # স্ক্রিনশট ২ অনুযায়ী: আউট অফ ক্রেডিট মেসেজ
                out_of_credit_msg = (
                    "🚨 **Oops! You're out of credits!** 🥲\n\n"
                    "💡 But don't worry — getting more is super easy:\n"
                    "1️⃣ Tap the button below 👇\n"
                    "2️⃣ Complete a quick task ✅\n"
                    "3️⃣ Instantly receive **10 free credits** to use the bot! 🚀\n\n"
                    "🆓 100% FREE — every single time!\n"
                    "🔄 You can earn **10 credits** again and again!\n\n"
                    "📌 **Need help?** Check out our tutorial guide!\n\n"
                    "🛠 **Facing issues?** Message us here: None\n\n"
                    "Let's keep the fun going! 🎉💥"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Refer and get 5 credit", url=f"https://t.me/share/url?url={get_refer_link(uid)}&text=Join%20this%20bot%20to%20get%20exclusive%20videos!")],
                    [InlineKeyboardButton(text="❓ How to Use the Bot", url="https://t.me/genzexposed")]
                ])
                await message.answer(out_of_credit_msg, reply_markup=kb)
                return

    # সাধারণ স্টার্ট মেসেজ
    await message.answer(f"Welcome {name}! Use the menu below to navigate.", reply_markup=get_main_menu())

# ৫. ওয়ালেট এবং অন্যান্য বাটন হ্যান্ডলার
@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    
    # স্ক্রিনশট ৩ ও ৪ অনুযায়ী ওয়ালেট লুক
    wallet_txt = (
        f"👤 **User:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {user['credits']}\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "✨ **Note:** You can earn **10 free credits** every time you watch a short ad.\n\n"
        "💸 **Don't want to watch ads?** You can also **buy credits** directly from the button below.\n\n"
        "🎉 Let's keep the fun going!"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Refer to Earn", url=f"https://t.me/share/url?url={get_refer_link(uid)}&text=Join%20now!")],
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    
    await message.answer(wallet_txt, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text.in_(["Get channels", "/get_channels"]))
async def get_channels_handler(message: types.Message):
    await message.answer("No backup channel found.")

@dp.message(F.text.in_(["Buy credits", "/buy"]))
async def buy_credits_handler(message: types.Message):
    # আকর্ষণীয় অ্যাডমিন কন্টাক্ট মেসেজ
    buy_txt = (
        "💎 **Upgrade Your Credits Today!** 💎\n\n"
        "ভিডিও দেখতে দেখতে ক্রেডিট শেষ? চিন্তা নেই! এখনই স্বল্প মূল্যে ক্রেডিট কিনে নিন এবং আনলিমিটেড এক্সেস পান।\n\n"
        "✨ **অফার:** ৫০ টাকায় ১০০ ক্রেডিট!\n\n"
        f"📩 সরাসরি যোগাযোগ করুন এডমিনের সাথে: @{ADMIN_USERNAME}\n\n"
        "নিচের বাটনে ক্লিক করে মেসেজ দিন এবং আপনার আইডিটি স্ক্রিনশট দিন।"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await message.answer(buy_txt, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "Start the bot")
async def start_button_handler(message: types.Message):
    await start_cmd(message, CommandObject(args=None))

# --- ৬. অ্যাডমিন ফিচারস ---

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def admin_video_upload(message: types.Message):
    v_key = f"vid{random.randint(1000, 9999)}"
    await video_links_col.insert_one({"video_key": v_key, "file_id": message.video.file_id})
    link = f"https://t.me/{BOT_USERNAME}?start={v_key}"
    await message.answer(f"✅ **ভিডিও সেভ হয়েছে!**\n\n🔗 লিঙ্ক:\n`{link}`", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_"))
async def check_callback(callback: types.CallbackQuery):
    v_key = callback.data.split("_")[1]
    if await is_subscribed(callback.from_user.id):
        await callback.answer("✅ Subscribed!", show_alert=True)
        await callback.message.delete()
        # সাবস্ক্রিপশন শেষে ধন্যবাদ মেসেজ পাঠানো
        await bot.send_message(callback.from_user.id, "thank you for joining all channels.")
        # ভিডিও রিকোয়েস্ট রি-ডিরেক্ট
        await start_cmd(callback.message, CommandObject(args=v_key))
    else: 
        await callback.answer("❌ Please join first!", show_alert=True)

# ব্রডকাস্টিং এবং ক্রেডিট অ্যাড আগের মতোই কাজ করবে...
@dp.message(Command("add"))
async def cmd_add(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split(); target_id, amt = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amt}})
        await message.answer(f"✅ ID `{target_id}` added `{amt}` credits.")
    except: await message.answer("❌ `/add ID Amount`")

# --- ৭. রানার ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(start_fake_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
        
