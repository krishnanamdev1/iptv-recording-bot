import os
import json
from datetime import datetime, timedelta
import aiofiles
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, ADMIN_FILE
from utils.admin_checker import remove_temp_admin

async def add_temp_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("⚠️ Unauthorized.")
        return

    parts = update.message.text.split()
    if len(parts) != 3:
        await update.message.reply_text("Usage: /addadmin user_id HH:MM:SS")
        return

    try:
        user_id = str(parts[1])
        hours, minutes, seconds = map(int, parts[2].split(":"))
        expiry_time = datetime.now() + timedelta(hours=hours, minutes=minutes, seconds=seconds)
        expiry_str = expiry_time.strftime("%Y-%m-%d %H:%M:%S")

        admins = {}
        if os.path.exists(ADMIN_FILE):
            async with aiofiles.open(ADMIN_FILE, "r") as f:
                content = await f.read()
                if content:
                    admins = json.loads(content)

        admins[user_id] = expiry_str

        async with aiofiles.open(ADMIN_FILE, "w") as f:
            await f.write(json.dumps(admins, indent=2))

        await update.message.reply_text(
            f"✅ Temporary admin `{user_id}` added till `{expiry_str}`",
            parse_mode="Markdown"
        )
        
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 *Admin Access Granted!*\n\n"
                 f"You have been granted temporary admin access for `{expiry_str}` hours.\n\n"
                 f"Thank you for your patience! 😊",
            parse_mode="Markdown"
        )
        
        
        
        
        

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("⚠️ Unauthorized.")
        return

    parts = update.message.text.split()
    if len(parts) != 2:
        await update.message.reply_text("Usage: /removeadmin user_id")
        return

    user_id = parts[1]

    if await remove_temp_admin(user_id):
        await update.message.reply_text(
            f"✅ Temporary admin `{user_id}` removed successfully.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"⚠️ User ID `{user_id}` not found in the admin list.",
            parse_mode="Markdown"
        )
