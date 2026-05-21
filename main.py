import logging
import asyncio
import os
import time
import psutil
import random
import uuid  
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from motor.motor_asyncio import AsyncIOMotorClient

API_TOKEN = "8565287860:AAEuYopIrpt9UtZLXMLxC_ceo5z-fOTsT8M"
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:Ratul1234@mybotdatabase.5m5engl.mongodb.net/?retryWrites=true&w=majority"
ADMIN_ID = 6793604200 
CHANNEL_ID = -1003960638119
LOG_CHANNEL_ID = -1003943039065  
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot"
START_TIME = time.time()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client["video_bot_db"]
users_col = db["users"]
video_links_col = db["video_links"]
delete_queue_col = db["delete_queue"]

class CooldownMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 2):
        super().__init__()
        self.limit = limit
        self.cooldowns = {}

    async def __call__(self, handler, event: types.Update, data: dict):
        user = None
        is_callback = False
        if isinstance(event, types.Message):
            user = event.from_user
        elif isinstance(event, types.CallbackQuery):
            user = event.from_user
            is_callback = True
        if user:
            if await is_admin(user.id):
                return await handler(event, data)
            current_time = time.time()
            last_time = self.cooldowns.get(user.id, 0)
            if current_time - last_time < self.limit:
                if is_callback:
                    try:
                        await event.answer("⚠️ Please wait... Don't spam!", show_alert=True)
                    except:
                        pass
                return
            self.cooldowns[user.id] = current_time
        return await handler(event, data)

dp.message.middleware(CooldownMiddleware(limit=2))
dp.callback_query.middleware(CooldownMiddleware(limit=2))

async def send_log(text):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Log error: {e}")

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Subscription check error for {user_id}: {e}")
        return False

async def auto_delete_scheduler(bot: Bot):
    logging.info("🚀 Background Auto-Delete Scheduler Started...")
    while True:
        try:
            now = datetime.utcnow()
            expired_tasks = delete_queue_col.find({"expire_at": {"$lte": now}})
            async for task in expired_tasks:
                chat_id = task["chat_id"]
                message_id = task["message_id"]
                task_id = task["_id"]
                try:
                    await bot.delete_message(chat_id, message_id)
                except TelegramBadRequest:
                    pass
                except Exception as e:
                    logging.error(f"Scheduler failed to delete message {message_id}: {e}")
                await delete_queue_col.delete_one({"_id": task_id})
                await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Error in auto_delete_scheduler: {e}")
        await asyncio.sleep(10)

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Start the bot"), KeyboardButton(text="Check your wallet")],
            [KeyboardButton(text="🎁 Claim Free Credit"), KeyboardButton(text="Get channels")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def is_admin(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    user = await users_col.find_one({"user_id": user_id})
    if user and user.get("is_admin") is True:
        return True
    return False

@dp.callback_query(F.data.startswith("check_"))
async def check_subscription_callback(call: types.CallbackQuery):
    uid = call.from_user.id
    name = call.from_user.full_name
    args = call.data.replace("check_", "")
    user_check = await users_col.find_one({"user_id": uid})
    if user_check and user_check.get("is_banned"):
        await call.answer("🚫 আপনি নিষিদ্ধ (Banned) আছেন।", show_alert=True)
        return
    try:
        if await is_subscribed(uid):
            current_verify_count = user_check.get("left_count", 0) if user_check else 0
            new_verify_count = current_verify_count + 1
            if new_verify_count >= 5:
                await users_col.update_one(
                    {"user_id": uid}, 
                    {
                        "$set": {"is_banned": True, "left_count": new_verify_count},
                        "$setOnInsert": {"credits": 10, "name": name, "joined_at": datetime.utcnow()}
                    }, 
                    upsert=True
                )
                await call.answer("🚫 বারবার চ্যানেল থেকে লিভ নিয়ে নিয়ম ভঙ্গ করায় আপনাকে ব্যান করা হয়েছে!", show_alert=True)
                await call.message.delete()
                await bot.send_message(uid, "🚫 বারবার চ্যানেল থেকে লিভ নেওয়ার কারণে আপনাকে এই বট থেকে নিষিদ্ধ করা হয়েছে।")
                await send_log(f"🚨 **Auto Banned for Leave & Re-Verify Spamming**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`\n📉 **Total Verify Attempts:** {new_verify_count}")
                return
            is_actually_new = False
            if not user_check or "credits" not in user_check:
                is_actually_new = True
            if is_actually_new:
                credits = 10
                log_msg = f"🆕 **New User Registered**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`\n📊 **Verify Count:** {new_verify_count}/5"
                if args.startswith("ref_"):
                    try:
                        ref_id = int(args.split("_")[1])
                        if ref_id != uid:
                            await users_col.update_one({"user_id": ref_id}, {"$inc": {"credits": 5}})
                            try: await bot.send_message(ref_id, f"🎉 {name} আপনার লিঙ্কে জয়েন করেছে! আপনি ৫ ক্রেডিট পেয়েছেন।")
                            except: pass
                            credits += 2
                            log_msg += f"\n🤝 **Referrer ID:** `{ref_id}` (Got 5 credits)"
                    except: pass
                await users_col.update_one(
                    {"user_id": uid},
                    {"$set": {"credits": credits, "name": name, "joined_at": datetime.utcnow(), "left_count": new_verify_count, "is_banned": False}},
                    upsert=True
                )
                await send_log(log_msg)
            else:
                await users_col.update_one(
                    {"user_id": uid}, 
                    {"$set": {"left_count": new_verify_count}}
                )
                await send_log(f"⚠️ **User Re-Verified (Left & Returned)**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`\n📊 **Total Verify Count:** {new_verify_count}/5")
            await call.answer("✅ Thank you for joining!", show_alert=False)
            await call.message.delete()
            await bot.send_message(uid, f"Welcome back, {call.from_user.full_name}!", reply_markup=get_main_menu())
        else:
            await call.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)
    except Exception as e:
        logging.error(f"Callback error: {e}")
        await call.answer("❌ Error occurred!", show_alert=True)

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    args = command.args or ""
    name = message.from_user.full_name
    user_data = await users_col.find_one({"user_id": uid})
    if user_data and user_data.get("is_banned"):
        await message.answer("🚫 আপনি এই বটটি ব্যবহার করার জন্য নিষিদ্ধ (Banned)।")
        return
    if await is_subscribed(uid):
        is_actually_new = False
        if not user_data or "credits" not in user_data:
            is_actually_new = True
        if is_actually_new:
            credits = 10
            log_msg = f"🆕 **New User Registered**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`\n📊 **Verify Count:** 1/5"
            if args.startswith("ref_"):
                try:
                    ref_id = int(args.split("_")[1])
                    if ref_id != uid:
                        await users_col.update_one({"user_id": ref_id}, {"$inc": {"credits": 5}})
                        try: await bot.send_message(ref_id, f"🎉 {name} আপনার লিঙ্কে জয়েন করেছে! আপনি ৫ ক্রেডিট পেয়েছেন।")
                        except: pass
                        credits += 2
                        log_msg += f"\n🤝 **Referrer ID:** `{ref_id}` (Got 5 credits)"
                except: pass
            await users_col.update_one(
                {"user_id": uid},
                {"$set": {"credits": credits, "name": name, "joined_at": datetime.utcnow(), "left_count": 1, "is_banned": False}},
                upsert=True
            )
            await send_log(log_msg)
            user_data = await users_col.find_one({"user_id": uid})
    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📂 Check Again", callback_data=f"check_{args or 'none'}")]
        ])
        await message.answer("⚠️ You must join our channel first to use the bot!", reply_markup=kb)
        return
    if args.startswith("vid"):
        if not user_data or user_data.get("credits", 0) < 1:
            await message.answer("❌ আপনার পর্যাপ্ত ক্রেডিট নেই! ভিডিও দেখতে ক্রেডিট অর্জন করুন বা রেফার করুন।")
            return
        video_data = await video_links_col.find_one({"video_key": args})
        if video_data:
            await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
            sent_video = await bot.send_video(chat_id=uid, video=video_data["file_id"])
            notif_msg = await message.answer("⚠️ **Security Alert:** This video will be deleted in **10 minutes**.")
            await send_log(f"📺 **Video Viewed**\n👤 **Name:** {name}\n🆔 **ID:** `{uid}`\n🔑 **Key:** `{args}`\n💰 **Status:** 1 Credit deducted")
            expire_time = datetime.utcnow() + timedelta(seconds=600)
            await delete_queue_col.insert_many([
                {"chat_id": uid, "message_id": sent_video.message_id, "expire_at": expire_time},
                {"chat_id": uid, "message_id": notif_msg.message_id, "expire_at": expire_time}
            ])
            return
    await message.answer(f"🎉 Welcome {name}!\n\n💎 **Your starting credits:** 10", reply_markup=get_main_menu())

@dp.message(F.text == "🎁 Claim Free Credit")
async def claim_credit_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    if not user:
        await users_col.insert_one({"user_id": uid, "credits": 10, "name": message.from_user.full_name, "joined_at": datetime.utcnow(), "left_count": 0})
        user = await users_col.find_one({"user_id": uid})
    if user.get("is_banned"):
        return await message.answer("🚫 আপনি নিষিদ্ধ।")
    last_claim = user.get("last_claim_time")
    current_time = datetime.utcnow()
    if last_claim:
        wait_until = last_claim + timedelta(hours=18)
        if current_time < wait_until:
            remaining = wait_until - current_time
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return await message.answer(f"⏳ আপনি ইতিমধ্যে ক্রেডিট নিয়েছেন!\n\nআবার **{hours} ঘণ্টা {minutes} মিনিট** পর চেষ্টা করুন।")
    await users_col.update_one({"user_id": uid}, {"$inc": {"credits": 10}, "$set": {"last_claim_time": current_time}})
    await message.answer("🎉 অভিনন্দন! আপনি সফলভাবে **১০ ক্রেডিট** ক্লেইম করেছেন।\n\nপরবর্তী ক্লেইম ১৮ ঘণ্টা পর করতে পারবেন।")
    await send_log(f"🎁 **Credit Claimed**\n👤 **User:** {message.from_user.full_name}\n🆔 **ID:** `{uid}`\n💰 **Amount:** 10 Credits")

@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    if user and user.get("is_banned"): return await message.answer("🚫 আপনি নিষিদ্ধ।")
    current_credits = user.get("credits", 0) if user else 0
    refer_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    share_text = f"https://t.me/share/url?url={refer_link}&text=বটটি ব্যবহার করে ফ্রি ক্রেডিট পান!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Refer & Earn", url=share_text)],
        [InlineKeyboardButton(text="💎 Buy Credits", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    text = (
        f"👤 **User:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"💰 **Credits:** {current_credits}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "✨ **Note:** You can earn 10 free credits every time you watch a short ad.\n\n"
        "💰 Don't want to watch ads? Buy credits directly below.\n\n"
        "🎉 Let's keep the fun going!"
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("ban"))
async def ban_user(message: types.Message, command: CommandObject):
    if not await is_admin(message.from_user.id): return
    try:
        target_id = int(command.args)
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": True}}, upsert=True)
        await message.answer(f"✅ User `{target_id}` has been banned.")
        await send_log(f"🚫 **User Banned**\n🆔 **Target ID:** `{target_id}`\n👤 **By Admin:** `{message.from_user.id}`")
    except: await message.answer("❌ Format: `/ban [user_id]`")

@dp.message(Command("unban"))
async def unban_user(message: types.Message, command: CommandObject):
    if not await is_admin(message.from_user.id): return
    try:
        target_id = int(command.args)
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": False, "left_count": 0}})
        await message.answer(f"✅ User `{target_id}` has been unbanned.")
        await send_log(f"🔓 **User Unbanned**\n🆔 **Target ID:** `{target_id}`\n👤 **By Admin:** `{message.from_user.id}`")
    except: await message.answer("❌ Format: `/unban [user_id]`")

@dp.message(Command("add"))
async def add_credits(message: types.Message, command: CommandObject):
    if not await is_admin(message.from_user.id): return
    try:
        args = command.args.split()
        target_id, amount = int(args[0]), int(args[1])
        await users_col.update_one({"user_id": target_id}, {"$inc": {"credits": amount}}, upsert=True)
        await message.answer(f"✅ Added {amount} credits to `{target_id}`")
        await send_log(f"💰 **Manual Credit Added**\n🆔 **To ID:** `{target_id}`\n💵 **Amount:** {amount}\n👤 **By Admin:** `{message.from_user.id}`")
    except: await message.answer("❌ Format: `/add [user_id] [amount]`")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not await is_admin(message.from_user.id): return
    total_users = await users_col.count_documents({})
    text = f"⚡ **BOT STATUS**\n\n👥 **Total Users:** {total_users}\n💻 **CPU:** {psutil.cpu_percent()}%\n\n`/add [id] [amount]`\n`/ban [id]` | `/unban [id]`\n`/broadcast [Reply to Text/Photo]`"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_handler(message: types.Message):
    if not await is_admin(message.from_user.id): return
    if not message.reply_to_message:
        return await message.reply("⚠️ **ভুল ফরম্যাট!** যেকোনো মেসেজ বা ফটোর রিপ্লাইয়ে `/broadcast` লিখুন।")
    reply = message.reply_to_message
    status_msg = await message.answer("⏳ **বস,F@,ব্রডকাস্ট প্রসেস শুরু হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।**")
    cursor = users_col.find({})
    total_users = await users_col.count_documents({})
    success_count = 0
    failed_count = 0
    async for user in cursor:
        target_id = user["user_id"]
        try:
            if reply.photo:
                await bot.send_photo(
                    chat_id=target_id, 
                    photo=reply.photo[-1].file_id, 
                    caption=reply.caption, 
                    parse_mode="Markdown" if reply.caption else None
                )
            else:
                await bot.send_message(chat_id=target_id, text=reply.text, parse_mode="Markdown" if reply.text else None)
            success_count += 1
            await asyncio.sleep(0.05) 
        except (TelegramForbiddenError, TelegramBadRequest):
            failed_count += 1
        except Exception as e:
            failed_count += 1
    report_text = (
        f"📢 **Broadcast Completed!**\n\n"
        f"👥 **Total Users in DB:** {total_users}\n"
        f"✅ **Successfully Sent:** {success_count}\n"
        f"❌ **Failed / Blocked:** {failed_count}"
    )
    await status_msg.edit_text(report_text, parse_mode="Markdown")

@dp.message(F.video)
async def handle_admin_video(message: types.Message):
    if not await is_admin(message.from_user.id): return
    file_id = message.video.file_id
    video_key = f"vid_{str(uuid.uuid4())[:8]}"
    await video_links_col.insert_one({"video_key": video_key, "file_id": file_id, "created_at": datetime.utcnow()})
    await message.answer(f"✅ **Video Saved!**\n🔗 Link: `https://t.me/{BOT_USERNAME}?start={video_key}`", parse_mode="Markdown")

@dp.message(Command("makeadmin"))
async def promote_to_admin(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(command.args)
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_admin": True}}, upsert=True)
        await message.answer(f"✅ User `{target_id}` কে সফলভাবে **Admin** বানানো হয়েছে।")
        await send_log(f"👑 **New Admin Promoted**\n🆔 **Target ID:** `{target_id}`\n👤 **By Main Admin:** `{message.from_user.id}`")
        try: await bot.send_message(target_id, "🎉 অভিনন্দন! আপনাকে এই বটের এডমিন প্যানেলের অ্যাক্সেস দেওয়া হয়েছে।")
        except: pass
    except:
        await message.answer("❌ ফরম্যাট ভুল! সঠিক ফরম্যাট: `/makeadmin [user_id]`")

@dp.message(Command("rmadmin"))
async def demote_from_admin(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(command.args)
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_admin": False}})
        await message.answer(f"❌ User `{target_id}` কে এডমিন পদ থেকে অপসারণ করা হয়েছে।")
        await send_log(f"📉 **Admin Demoted**\n🆔 **Target ID:** `{target_id}`\n👤 **By Main Admin:** `{message.from_user.id}`")
    except:
        await message.answer("❌ ফরম্যাট ভুল! সঠিক ফরম্যাট: `/rmadmin [user_id]`")

@dp.message(F.chat.type == "private")
async def unknown(message: types.Message):
    uid = message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    if user and user.get("is_banned"): return
    await message.answer("❓ **Unknown command!**", reply_markup=get_main_menu())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(auto_delete_scheduler(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
