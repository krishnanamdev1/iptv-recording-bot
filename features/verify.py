import requests
import secrets
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler,CallbackQueryHandler
from config import (
    VERIFICATION_LINKS,
    VERIFICATION_BASE_URL,
    BOT_NAME,
    VERIFICATION_REWARD_MINUTES
)

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send verification link to user"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Generate unique token
    token = secrets.token_urlsafe(16)
    verification_url = f"https://t.me/{BOT_NAME}?start=verify_{token}"
    
    # Shorten with VPLinks
    try:
        response = requests.get(f"{VERIFICATION_BASE_URL}{verification_url}")
        if response.status_code == 200:
            short_url = response.json().get('shortenedUrl', verification_url)
        else:
            short_url = verification_url
    except Exception:
        short_url = verification_url
    
    # Store verification token
    VERIFICATION_LINKS[token] = {
        'user_id': user_id,
        'chat_id': chat_id,
        'created_at': datetime.now(),
        'used': False
    }
    
    # Send message with button
    keyboard = [
        [InlineKeyboardButton("🔗 Verify Now", url=short_url)],
        [InlineKeyboardButton("✅ I've Verified", callback_data=f"verify_check_{token}")]
    ]
    
    await update.message.reply_text(
        f"To verify and get {VERIFICATION_REWARD_MINUTES} minutes recording access:\n\n"
        "1. Click the button below\n"
        "2. Complete the verification\n"
        "3. Click 'I've Verified'\n\n"
        "Note: This link expires in 10 minutes",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verification callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('verify_check_'):
        token = query.data.split('_')[-1]
        verification = VERIFICATION_LINKS.get(token)
        
        if not verification:
            await query.edit_message_text("❌ Invalid or expired verification link")
            return
            
        if verification['used']:
            await query.edit_message_text("⚠️ This link has already been used")
            return
            
        # Mark as used
        VERIFICATION_LINKS[token]['used'] = True
        
        # Add recording time to user's account (you'll need to implement this)
        user_id = verification['user_id']
        expiry_time = datetime.now() + timedelta(minutes=VERIFICATION_REWARD_MINUTES)
        
        # Store verification in your user database
        # Implement your own user time tracking system here
        # Example: user_db[user_id]['recording_expiry'] = expiry_time
        
        await query.edit_message_text(
            f"✅ Verification successful!\n\n"
            f"You can now record for {VERIFICATION_REWARD_MINUTES} minutes "
            f"(until {expiry_time.strftime('%H:%M')})"
        )

def setup_verify_handlers(application):
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_check_"))
