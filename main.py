import logging
import asyncio
import os
import time
import psutil
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.exceptions import TelegramBadRequest

from motor.motor_asyncio import AsyncIOMotorClient

# =========================
# CONFIG
# =========================
API_TOKEN = "8565287860:AAHqxvFGov9qwtFcmI78qVmB_KFf-24ZJ9o"
MONGO_URL = "mongodb+srv://itsmeratul3_db_user:Ratul1234@mybotdatabase.5m5engl.mongodb.net/?retryWrites=true&w=majority"

ADMIN_ID = 6793604200  # âœ… à¦à¦Ÿà¦¿ int à¦¹à¦¿à¦¸à§‡à¦¬à§‡ à¦¸à§‡à¦Ÿ à¦•à¦°à¦¾ à¦¹à§Ÿà§‡à¦›à§‡
CHANNEL_ID = -1003960638119
CHANNEL_URL = "https://t.me/+iIe1XRdmMr5kNzFl"
ADMIN_USERNAME = "artist_x0"
BOT_USERNAME = "Genz2027bot"

START_TIME = time.time()

# =========================
# INIT
# =========================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

client = AsyncIOMotorClient(MONGO_URL)
db = client["video_bot_db"]
users_col = db["users"]
video_links_col = db["video_links"]

# =========================
# HELPERS
# =========================
async def is_subscribed(user_id):
    """âœ… Channel subscription check - improved error handling"""
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Subscription check error for {user_id}: {e}")
        return False

async def auto_delete_video(chat_id, msg_id, seconds=600):
    """âœ… Auto delete video after specified time"""
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception as e:
        logging.error(f"Auto delete failed: {e}")

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Start the bot"), KeyboardButton(text="Check your wallet")],
            [KeyboardButton(text="Buy credits"), KeyboardButton(text="Get channels")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_refer_link(uid):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

# =========================
# ADMIN CHECKER
# =========================
def is_admin(user_id: int) -> bool:
    """âœ… Admin checker - à¦¸à¦¬ à¦œà¦¾à§Ÿà¦—à¦¾à§Ÿ à¦à¦Ÿà¦¾à¦‡ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à§à¦¨"""
    return user_id == ADMIN_ID

# =========================
# HANDLERS
# =========================

@dp.callback_query(F.data.startswith("check_"))
async def check_subscription_callback(call: types.CallbackQuery):
    """âœ… Check Again button handler"""
    uid = call.from_user.id
    try:
        if await is_subscribed(uid):
            await call.answer("âœ… Thank you for joining!", show_alert=False)
            await call.message.delete()
            await bot.send_message(uid, f"Welcome back, {call.from_user.full_name}!", reply_markup=get_main_menu())
        else:
            await call.answer("âš ï¸ You still haven't joined the channel!", show_alert=True)
    except Exception as e:
        await call.answer("âŒ Error occurred!", show_alert=True)
        logging.error(f"Check callback error: {e}")

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    """âœ… Start command - Fixed referral system"""
    uid = message.from_user.id
    args = command.args or ""
    name = message.from_user.full_name

    # Subscription check
    if not await is_subscribed(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ðŸ“¢ Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="ðŸ“ Check Again", callback_data=f"check_{args or 'none'}")]
        ])
        await message.answer("âš ï¸ You must join our channel first to use the bot!", reply_markup=kb)
        return

        # Video delivery à¦“ à¦¸à¦¾à¦‡à¦²à§‡à¦¨à§à¦Ÿ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦¡à¦¿à¦¡à¦¾à¦•à¦¶à¦¨ (à§§ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ)
    if args and args.startswith("vid"):
        user = await users_col.find_one({"user_id": uid})
        
        # à¦šà§‡à¦•: à¦‡à¦‰à¦œà¦¾à¦°à§‡à¦° à¦…à¦¨à§à¦¤à¦¤ à§§ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦†à¦›à§‡ à¦•à¦¿ à¦¨à¦¾
        if not user or user.get("credits", 0) < 1:
            await message.answer("âŒ à¦†à¦ªà¦¨à¦¾à¦° à¦ªà¦°à§à¦¯à¦¾à¦ªà§à¦¤ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦¨à§‡à¦‡! à¦­à¦¿à¦¡à¦¿à¦“ à¦¦à§‡à¦–à¦¤à§‡ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦…à¦°à§à¦œà¦¨ à¦•à¦°à§à¦¨ à¦¬à¦¾ à¦°à§‡à¦«à¦¾à¦° à¦•à¦°à§à¦¨à¥¤")
            return

        video_data = await video_links_col.find_one({"video_key": args})
        if video_data:
            try:
                # à§§ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦•à§‡à¦Ÿà§‡ à¦¨à§‡à¦“à§Ÿà¦¾ à¦¹à¦šà§à¦›à§‡ (à¦¸à¦¾à¦‡à¦²à§‡à¦¨à§à¦Ÿà¦²à¦¿)
                await users_col.update_one({"user_id": uid}, {"$inc": {"credits": -1}})
                
                sent_video = await bot.send_video(chat_id=uid, video=video_data["file_id"])
                notif_msg = await message.answer("âš ï¸ **Security Alert:** This video will be deleted in **10 minutes**.")
                
                asyncio.create_task(auto_delete_video(uid, sent_video.message_id, 600))
                asyncio.create_task(auto_delete_video(uid, notif_msg.message_id, 600))
                return
            except Exception as e:
                await message.answer("âŒ Video sending failed!")
                logging.error(f"Video send error: {e}")
                return
                

    # User registration & Referral system âœ… FIXED
    user = await users_col.find_one({"user_id": uid})
    if not user:
        credits = 10  # Default credits
        
        # Referral logic âœ… FIXED - à¦à¦–à¦¾à¦¨à§‡ à¦¸à¦®à¦¸à§à¦¯à¦¾ à¦›à¦¿à¦²
        if args and args.startswith("ref_"):
            try:
                ref_id_str = args.split("_")[1]
                ref_id = int(ref_id_str)
                if ref_id != uid and ref_id > 0:
                    # Check if referrer exists
                    referrer = await users_col.find_one({"user_id": ref_id})
                    if referrer:
                        await users_col.update_one(
                            {"user_id": ref_id}, 
                            {"$inc": {"credits": 5}}, 
                            upsert=False
                        )
                        try:
                            await bot.send_message(
                                ref_id, 
                                "ðŸŽ‰ Someone joined using your referral link! You got **5 credits**.",
                                parse_mode="Markdown"
                            )
                        except:
                            pass  # Referrer blocked bot or deleted account
                        credits += 2  # Bonus for joining via referral
            except (ValueError, IndexError):
                logging.error(f"Invalid referral format: {args}")
        
        # Insert new user âœ… FIXED
        await users_col.insert_one({
            "user_id": uid, 
            "credits": credits, 
            "name": name, 
            "joined_at": datetime.utcnow()
        })
        logging.info(f"New user registered: {uid}, credits: {credits}")

    # Send welcome message
    try:
        await message.answer(
            f"ðŸŽ‰ Welcome {name}!\n\nðŸ’Ž **Your starting credits:** 10\n\nChoose an option below:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        await message.answer(f"Welcome {name}!", reply_markup=get_main_menu())


# --- Wallet Handler (à¦¯à¦–à¦¨ à¦‡à¦‰à¦œà¦¾à¦° 'Check your wallet' à¦ à¦•à§à¦²à¦¿à¦• à¦•à¦°à¦¬à§‡) ---
@dp.message(F.text.in_(["Check your wallet", "/wallet"]))
async def wallet_handler(message: types.Message):
    await send_wallet_info(message)

# --- Callback Handler (à¦¯à¦–à¦¨ à¦‡à¦‰à¦œà¦¾à¦° à¦¬à¦¾à¦Ÿà¦¨à§‡ à¦•à§à¦²à¦¿à¦• à¦•à¦°à¦¬à§‡) ---
@dp.callback_query(lambda c: c.data in ["refer_info", "buy_credits"])
async def wallet_callback_handler(callback_query: types.CallbackQuery):
    await send_wallet_info(callback_query.message)
    await callback_query.answer()

# --- à¦•à¦®à¦¨ à¦«à¦¾à¦‚à¦¶à¦¨ à¦¯à¦¾ à¦¬à¦¾à¦Ÿà¦¨ à¦à¦¬à¦‚ à¦Ÿà§‡à¦•à§à¦¸à¦Ÿ à¦ªà¦¾à¦ à¦¾à¦¬à§‡ ---
async def send_wallet_info(message: types.Message):
    uid = message.chat.id if message.chat else message.from_user.id
    user = await users_col.find_one({"user_id": uid})
    
    # à¦¡à¦¾à¦Ÿà¦¾à¦¬à§‡à¦¸ à¦¥à§‡à¦•à§‡ à¦°à¦¿à§Ÿà§‡à¦² à¦Ÿà¦¾à¦‡à¦® à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦šà§‡à¦• (à¦à¦¡à¦®à¦¿à¦¨ à¦¬à¦¾à§œà¦¾à¦²à§‡ à¦à¦–à¦¾à¦¨à§‡ à¦¬à¦¾à§œà¦¬à§‡)
    current_credits = user.get("credits", 0) if user else 0
    
    # à¦†à¦ªà¦¨à¦¾à¦° à¦¦à§‡à¦“à§Ÿà¦¾ à¦‡à¦‰à¦œà¦¾à¦°à¦¨à§‡à¦®à¦—à§à¦²à§‹
    bot_username = "Genz2027bot"
    admin_username = "artist_x0"
    
    # à¦°à§‡à¦«à¦¾à¦°à§‡à¦² à¦“ à¦¶à§‡à§Ÿà¦¾à¦° à¦²à¦¿à¦™à§à¦•
    refer_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    share_text = f"https://t.me/share/url?url={refer_link}&text=à¦¬à¦Ÿà¦Ÿà¦¿ à¦¬à§à¦¯à¦¬à¦¹à¦¾à¦° à¦•à¦°à§‡ à¦«à§à¦°à¦¿ à¦•à§à¦°à§‡à¦¡à¦¿à¦Ÿ à¦ªà¦¾à¦¨ à¦à¦¬à¦‚ à¦ªà§à¦°à¦¿à¦®à¦¿à§Ÿà¦¾à¦® à¦­à¦¿à¦¡à¦¿à¦“ à¦¦à§‡à¦–à§à¦¨!"

    # à¦¬à¦¾à¦Ÿà¦¨ à¦¸à§‡à¦Ÿà¦†à¦ª
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ðŸ¤ Refer & Earn", url=share_text)],
        [InlineKeyboardButton(text="ðŸ’Ž Buy Credits", url=f"https://t.me/{admin_username}")]
    ])

    # à¦†à¦ªà¦¨à¦¾à¦° à¦¦à§‡à¦“à§Ÿà¦¾ à¦¹à§à¦¬à¦¹à§ à¦«à¦°à¦®à§à¦¯à¦¾à¦Ÿ
    text = (
        f"ðŸ‘¤ **User:** {message.chat.full_name if message.chat.full_name else 'User'}\n"
        f"ðŸ†” **User ID:** `{uid}`\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f"ðŸ’° **Credits:** {current_credits}\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        "âœ¨ **Note:** You can earn 10 free credits every time you watch a short ad.\n\n"
        "ðŸ’¸ Don't want to watch ads? You can also buy credits directly from the button below.\n\n"
        "ðŸŽ‰ Let's keep the fun going!"
    )
    
    try:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    except:
        await message.answer(text.replace("`", ""), reply_markup=kb)


# âœ… ADMIN COMMANDS - FIXED
@dp.message(Command("add"))
async def add_credits(message: types.Message, command: CommandObject):
    """âœ… Add credits - Admin only"""
    if not is_admin(message.from_user.id):
        return  # Silent ignore for non-admins
    
    try:
        args = command.args.split()
        if len(args) < 2:
            await message.answer("âŒ **Format:** `/add [user_id] [amount]`", parse_mode="Markdown")
            return
            
        target_id = int(args[0])
        amount = int(args[1])
        
        if amount <= 0:
            await message.answer("âŒ Amount must be positive!")
            return
            
        result = await users_col.update_one(
            {"user_id": target_id}, 
            {"$inc": {"credits": amount}}, 
            upsert=True
        )
        
        status = "âœ…" if result.modified_count > 0 else "ðŸ”„"
        await message.answer(f"{status} Added **{amount}** credits to user `{target_id}`", parse_mode="Markdown")
        
        # Notify user
        try:
            await bot.send_message(
                target_id, 
                f"ðŸ’° **Credits Added!**\n\n+{amount} credits have been added to your wallet!\n\nðŸ’Ž Check your balance:",
                parse_mode="Markdown"
            )
        except:
            await message.answer(f"âš ï¸ User `{target_id}` may have blocked the bot", parse_mode="Markdown")
            
    except ValueError:
        await message.answer("âŒ **Invalid format!** Use: `/add 123456789 50`", parse_mode="Markdown")
    except Exception as e:
        await message.answer("âŒ **Error occurred!**")
        logging.error(f"Add credits error: {e}")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """âœ… Admin panel - FIXED"""
    if not is_admin(message.from_user.id):
        return  # Silent ignore
    
    try:
        total_users = await users_col.count_documents({})
        uptime = int(time.time() - START_TIME)
        cpu = psutil.cpu_percent(interval=1)
        
        text = (
            f"âš¡ **BOT STATUS**\n\n"
            f"ðŸ‘¥ **Total Users:** {total_users}\n"
            f"ðŸ–¥ **CPU Usage:** {cpu}%\n"
            f"â± **Uptime:** {uptime//3600}h {(uptime%3600)//60}m\n"
            f"ðŸŒ **Channel:** {CHANNEL_URL}\n\n"
            f"**Commands:**\n"
            f"`/add [id] [amount]` - Add credits\n"
            f"`/admin` - Admin panel"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ðŸ”„ Refresh", callback_data="refresh_admin")],
            [InlineKeyboardButton(text="ðŸ“Š Users List", callback_data="users_list")]
        ])
        
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer("âŒ Error loading admin panel!")
        logging.error(f"Admin panel error: {e}")

@dp.message(F.text == "Buy credits")
async def buy_credits(message: types.Message):
    """âœ… Buy credits handler"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ðŸ’Ž Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton(text="ðŸ’° Check Wallet", callback_data="check_wallet")]
    ])
    await message.answer(
        f"ðŸ’Ž **Buy Credits**\n\n"
        f"ðŸ“ž Contact admin: @{ADMIN_USERNAME}\n\n"
        f"ðŸ’° **Rates:**\n"
        f"â€¢ 100 credits = $1\n"
        f"â€¢ 500 credits = $4\n"
        f"â€¢ 1000 credits = $7",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# =========================
# VIDEO TO LINK GENERATOR (ADMIN ONLY)
# =========================
@dp.message(F.video)
async def handle_admin_video(message: types.Message):
    """âœ… Admin à¦­à¦¿à¦¡à¦¿à¦“ à¦¦à¦¿à¦²à§‡ à¦²à¦¿à¦™à§à¦• à¦œà§‡à¦¨à¦¾à¦°à§‡à¦Ÿ à¦¹à¦¬à§‡"""
    if not is_admin(message.from_user.id):
        return 

    file_id = message.video.file_id
    video_key = f"vid_{random.getrandbits(32)}"
    
    await video_links_col.insert_one({
        "video_key": video_key,
        "file_id": file_id,
        "created_at": datetime.utcnow()
    })
    
    share_link = f"https://t.me/{BOT_USERNAME}?start={video_key}"
    
    text = (
        "âœ… **Video Saved Successfully!**\n\n"
        f"ðŸ”— **Your Link:** `{share_link}`"
    )
    
    await message.answer(text, parse_mode=None)
    


# Handle unknown commands
@dp.message()
async def unknown(message: types.Message):
    """âœ… Unknown message handler"""
    await message.answer(
        "â“ **Unknown command!**\n\n"
        "Use the buttons below:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

# =========================
# RUN BOT
# =========================
async def main():
    """âœ… Main function with proper startup"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("ðŸš€ Bot started successfully!")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot startup error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
