import shlex  # Add this import at the top
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils.admin_checker import is_temp_admin
from scheduler import schedule_recording
from utils.logging import log_to_channel
from config import ADMIN_ID


from telegram import Update
from telegram.ext import ContextTypes
from utils.admin_checker import is_temp_admin  # Import the function

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if the user is a permanent or temporary admin
    if user_id not in ADMIN_ID and not await is_temp_admin(user_id):
        await update.message.reply_text(
            "⚠️ *Unauthorized Access*\n\n"
            "You do not have permission to use this bot.\n"
            "Please request admin access using the /start command.",
            parse_mode="Markdown"
        )
        return
    
    # Proceed with the command logic
  #  await update.message.reply_text("Command executed successfully!")


    try:
        parts = shlex.split(update.message.text)
        if len(parts) < 7:
            await update.message.reply_text(
                "❗ *Invalid Format!*\n\n"
                "Use this format:\n"
                "`/schedule \"url\" DD-MM-YYYY HH:MM:SS duration channel title`",
                parse_mode="Markdown"
            )
            return

        url = parts[1].strip('"')
        date = parts[2]
        time_part = parts[3]
        duration = parts[4]
        channel = parts[5]
        title = " ".join(parts[6:])
        start_time_str = f"{date} {time_part}"

        try:
            datetime.strptime(start_time_str, "%d-%m-%Y %H:%M:%S")
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid date/time format!*\nUse `DD-MM-YYYY HH:MM:SS`",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"**Recording Scheduled Successfully!**\n\n"
            f"**Title:** `{title}`\n"
            f"**Channel:** `{channel}`\n"
            f"**Time:** `{start_time_str}`\n"
            f"**Duration:** `{duration}`",
            parse_mode="Markdown"
        )

        username = update.effective_user.username or "Unknown"
        await log_to_channel(context.bot, user_id, username, update.message.text, start_time_str, title)
        
        await schedule_recording(url, start_time_str, duration, channel, title, update.effective_chat.id, update.message.message_id)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")
