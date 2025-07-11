from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, ACTIVE_RECORDINGS
import asyncio
from datetime import datetime

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current active recordings"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_ID:
        await update.message.reply_text("❌ Only admin can use this command")
        return
    
    if not ACTIVE_RECORDINGS:
        await update.message.reply_text("ℹ️ No active recordings currently")
        return
    
    message = "📊 Current Active Recordings:\n\n"
    for recording_id, recording in ACTIVE_RECORDINGS.items():
        message += (
            f"📌 Title: {recording['title']}\n"
            f"📺 Channel: {recording['channel']}\n"
            f"⏱ Duration: {recording['duration']}\n"
            f"🕒 Started: {recording['start_time']}\n"
            f"👤 User: {recording['user_id']}\n\n"
        )
    
    await update.message.reply_text(message)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users with active recordings"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_ID:
        await update.message.reply_text("❌ Only admin can use this command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = "📢 Admin Broadcast:\n\n" + " ".join(context.args)
    
    # Get unique user IDs from active recordings
    user_ids = {recording['user_id'] for recording in ACTIVE_RECORDINGS.values()}
    
    if not user_ids:
        await update.message.reply_text("ℹ️ No active users to broadcast to")
        return
    
    success = 0
    failed = 0
    
    for chat_id in user_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            success += 1
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")
            failed += 1
        await asyncio.sleep(0.1)  # Rate limiting
    
    await update.message.reply_text(
        f"Broadcast complete!\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}"
    )

def add_active_recording(details):
    """Add a recording to active recordings tracking"""
    from config import ACTIVE_RECORDINGS
    import time
    recording_id = str(int(time.time()))  # Simple ID based on timestamp
    ACTIVE_RECORDINGS[recording_id] = {
        'title': details['title'],
        'channel': details['channel'],
        'duration': details['duration'],
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': details['user_id']
    }
    return recording_id

def remove_active_recording(recording_id):
    """Remove a recording from tracking"""
    from config import ACTIVE_RECORDINGS
    if recording_id in ACTIVE_RECORDINGS:
        del ACTIVE_RECORDINGS[recording_id]



# In a new file or existing database file
from datetime import datetime, timedelta

user_db = {}

def is_user_verified(user_id):
    """Check if user has active verification"""
    user = user_db.get(user_id, {})
    expiry = user.get('recording_expiry')
    return expiry and expiry > datetime.now()

def add_verification_time(user_id, minutes):
    """Add recording time to user"""
    if user_id not in user_db:
        user_db[user_id] = {}
    
    current_expiry = user_db[user_id].get('recording_expiry', datetime.now())
    new_expiry = current_expiry + timedelta(minutes=minutes)
    user_db[user_id]['recording_expiry'] = new_expiry
    return new_expiry
    

