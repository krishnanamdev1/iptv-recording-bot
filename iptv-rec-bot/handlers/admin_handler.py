from telegram import Update
from telegram.ext import ContextTypes
from utils.admin_checker import is_temp_admin  # Make sure to import this
from config import ADMIN_ID
from datetime import datetime
from utils.admin_checker import get_admin_expiry_time

async def handle_admin_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # First check permanent admin status
    is_permanent_admin = user.id in ADMIN_ID
    
    # Then check temporary admin status (only if not permanent admin)
    is_temp = False
    remaining_time = ""
    if not is_permanent_admin:
        is_temp = await is_temp_admin(user.id)
        if is_temp:
            expiry_time = await get_admin_expiry_time(user.id)
            if expiry_time:
                time_left = expiry_time - datetime.now()
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                remaining_time = (
                    f"\n\n⏳ Your temporary admin access expires in: "
                    f"{hours} hours, {minutes} minutes"
                )

    # Only show admin status message if they actually are an admin
    if is_permanent_admin or is_temp:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"🌟 *Admin Status*\n\n"
                 f"You already have admin access!\n"
                 f"{'⏳ This is a permanent admin account' if is_permanent_admin else remaining_time}\n\n"
                 f"No need to request again. 😊",
            parse_mode="Markdown"
        )
        return
    
    # Rest of the function for non-admin users...
    request_msg = (
        "🆕 *NEW ADMIN REQUEST* 🆕\n\n"
        f"👤 *Requester:* {user.first_name}\n"
        f"🆔 *User ID:* `{user.id}`\n"
    )

    if user.username:
        request_msg += f"🔗 @{user.username}\n"

    request_msg += (
        "\nTo grant temporary access:\n"
        f"`/add {user.id} 04:00:00` (for 4 hours)\n\n"
        "Or make permanent admin via config.py\n\n"
        f"Request received at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


    # Send to all admins
    for admin_chat_id in ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=request_msg,
                parse_mode="Markdown",
                disable_notification=False  # Make sure admins get notified
            )
        except Exception as e:
            print(f"Error notifying admin {admin_chat_id}: {e}")

    # Send confirmation to user - enhanced version
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    user_response = (
        "✅ *Admin Request Received*\n\n"
        "🔹 Your request has been sent to the bot admins.\n"
        "🔹 You'll receive a notification when approved.\n"
        "🔹 Average approval time: 6-12 hours.\n\n"
    
        "📌 *Important Notes:*\n"
        "• Temporary access will be granted (e.g., 4-12 hours initially).\n"
        "• Admins **will not** auto-approve requests.\n"
        "• For urgent requests, please contact the developer.\n\n"
    
        "Thank you for your patience! 😊"
    )

# Add the inline keyboard button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Help / Contact Developer", url="https://t.me/Requestadminuser_bot")]
    ])

    await context.bot.send_message(
        chat_id=user.id,
        text=user_response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    
    
    
    
    
async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extract user ID and duration from callback_data
    _, user_id, duration = query.data.split("_")
    user_id = int(user_id)
    duration = int(duration)
    
    # Add temporary admin
    expiry_time = (datetime.now() + timedelta(hours=duration)).strftime("%Y-%m-%d %H:%M:%S")
    await add_temp_admin(user_id, expiry_time)
    
    # Notify admin
    await query.edit_message_text(
        f"✅ Temporary admin access granted to user `{user_id}` for {duration} hours.",
        parse_mode="Markdown"
    )
    
    # Notify user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"🎉 *Admin Access Granted!*\n\n"
             f"You have been granted temporary admin access for {duration} hours.\n\n"
             f"Thank you for your patience! 😊",
        parse_mode="Markdown"
    )
        
    
 