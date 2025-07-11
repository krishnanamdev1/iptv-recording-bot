import os
from datetime import datetime
from pytz import timezone
from telegram import Bot
from telegram.constants import ParseMode
from config import LOG_CHANNEL, BOT_TOKEN

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return ''.join('\\' + char if char in escape_chars else char for char in text)

async def log_to_channel(bot: Bot, user_id: int, username: str, command: str, start_time_str: str, filename: str):
    """Async function to log events to Telegram channel."""
    try:
        # Get current IST time
        ist = timezone("Asia/Kolkata")
        current_time = datetime.now(ist).strftime("%d-%m-%Y %H:%M:%S")

        # Escape all special characters for MarkdownV2
        escaped_username = escape_markdown_v2(username)
        escaped_command = escape_markdown_v2(command)
        escaped_filename = escape_markdown_v2(filename)
        escaped_start_time = escape_markdown_v2(start_time_str)
        escaped_current_time = escape_markdown_v2(current_time)

        log_message = (
            "📝 *New Recording Log*\n\n"
            f"👤 *User:* `{escaped_username}` \\(ID: `{user_id}`\\)\n"
            f"⏰ *Time:* `{escaped_current_time}`\n"
            f"📂 *File:* `{escaped_filename}`\n"
            f"🔖 *Command:* `{escaped_command}`\n"
            f"⏱️ *Scheduled Time:* `{escaped_start_time}`"
        )

        await bot.send_message(
            chat_id=LOG_CHANNEL,
            text=log_message,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        print(f"Failed to log to channel: {e}")

# Make sure the function is exported
__all__ = ['log_to_channel']
