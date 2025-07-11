from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from utils.admin_checker import is_temp_admin
from config import ADMIN_ID
from telegram.constants import ParseMode

# --- Help Text Content ---

def get_main_help_text():
    return """
    🔸 *Bot Commands Help* 🔸

    Select a category below to see the available commands.
    """

def get_recording_help_text():
    return """
    🎥 *Recording Commands*

    *Instant Recording:*
    `/rec <url/id> <duration> [title]`
    - *url/id:* Direct stream URL or channel ID.
    - *duration:* In seconds (e.g., `300`) or HH:MM:SS (e.g., `01:30:00`).
    - *title:* (Optional) A title for your recording.

    *Scheduled Recording:*
    `/s <url/id> <datetime> <duration> [title]`
    - *datetime:* In `DD-MM-YYYY HH:MM:SS` format.
    
    *Find Channels:*
    `/find <query>` - Search for channels by name or ID.
    """

def get_admin_help_text():
    return """
    🛡️ *Admin Management*

    `/add <user_id> [duration]`
    - Adds a temporary admin.
    - *duration:* (Optional) e.g., `1h`, `2d`.
    
    `/rm <user_id>`
    - Removes an admin or temporary admin.
    """

def get_messaging_help_text():
    return """
    📩 *Messaging Commands*

    `/reply <user_id> <message>`
    - Sends a message to a specific user.

    `/broadcast <message>`
    - Sends a message to all users.
    
    *Reply to a forwarded message* to send a response directly to that user.
    """

# --- Keyboard Layouts ---

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎥 Recording", callback_data="help_recording"),
            InlineKeyboardButton("🛡️ Admin", callback_data="help_admin"),
        ],
        [
            InlineKeyboardButton("📩 Messaging", callback_data="help_messaging"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [[InlineKeyboardButton("« Back to Help", callback_data="help_main")]]
    return InlineKeyboardMarkup(keyboard)

# --- Handlers ---

async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_ID and not await is_temp_admin(user_id):
        await update.message.reply_text(
            "⚠️ *Unauthorized Access*\n\n"
            "You don't have permission to use this bot.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    await update.message.reply_text(
        get_main_help_text(),
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    help_section = query.data.split("_")[1]

    text = ""
    reply_markup = get_back_keyboard()

    if help_section == "main":
        text = get_main_help_text()
        reply_markup = get_main_keyboard()
    elif help_section == "recording":
        text = get_recording_help_text()
    elif help_section == "admin":
        text = get_admin_help_text()
    elif help_section == "messaging":
        text = get_messaging_help_text()

    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )

def get_help_handlers():
    return [
        CommandHandler("h", send_help),
        CallbackQueryHandler(help_callback, pattern="^help_"),
    ]

from telegram.ext import ContextTypes

# Define this at the top of your file Replace with actual admin ID

async def cancel_recording_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = int(query.data.split("_")[-1])
    
    # Check authorization
    if user_id != chat_id and user_id != ADMIN_ID:
        await query.answer("You are not authorized to cancel this recording.", show_alert=True)
        return

    # Cancel the recording
    recording_process = context.chat_data.get('recording_process')
    if recording_process:
        try:
            recording_process.terminate()
            await query.answer("Recording cancelled successfully", show_alert=True)
            await query.edit_message_text("⏹ Recording cancelled by user/admin.")
        except Exception as e:
            await query.answer(f"Error cancelling: {str(e)}", show_alert=True)
    else:
        await query.answer("No active recording to cancel", show_alert=True)

# In your main application setup:
