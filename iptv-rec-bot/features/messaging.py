import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from config import ADMIN_ID, LOG_CHANNEL
from features.auto_responses import AUTO_RESPONSES

# File to store message context
MESSAGE_CONTEXT_FILE = "message_context.json"

def load_context():
    """Load message context from JSON file"""
    if not os.path.exists(MESSAGE_CONTEXT_FILE):
        return {}
    with open(MESSAGE_CONTEXT_FILE, 'r') as f:
        return json.load(f)

def save_context(context_data):
    """Save message context to JSON file"""
    with open(MESSAGE_CONTEXT_FILE, 'w') as f:
        json.dump(context_data, f)

async def delete_after_delay(message, delay=2):
    """Delete message after specified delay"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler"""
    # Ignore messages not addressed to the bot
    if not (update.message.chat.type == "private" or 
            (update.message.reply_to_message and 
             update.message.reply_to_message.from_user.id == context.bot.id)):
        return

    user = update.message.from_user
    message = update.message.text

    # Check for auto-responses first
    message_lower = message.lower()
    for keyword, response in AUTO_RESPONSES.items():
        if keyword in message_lower:
            await update.message.reply_text(response)
            return

    # Store message context
    ctx = load_context()
    message_id = str(update.message.message_id)
    ctx[message_id] = {
        'user_id': user.id,
        'chat_id': update.message.chat_id,
        'is_group': update.message.chat.type != "private",
        'original_msg_id': update.message.message_id
    }
    save_context(ctx)

    # Forward to admins only for direct messages
    if update.message.chat.type == "private":
        for admin in ADMIN_ID:
            try:
                forwarded = await context.bot.forward_message(
                    chat_id=admin,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                
                # Store admin context
                ctx[str(forwarded.message_id)] = {
                    'source_message_id': message_id,
                    'is_admin_copy': True
                }
                save_context(ctx)
                
            except Exception as e:
                print(f"Error forwarding to admin {admin}: {e}")

        # Log and confirm
        if LOG_CHANNEL:
            await context.bot.send_message(
                LOG_CHANNEL,
                f"#Message\nFrom: {user.full_name} (@{user.username or 'None'})\n"
                f"ID: {user.id}\nChat: {update.message.chat_id}\nMsg: {message}"
            )
        
        confirmation = await update.message.reply_text("✅ Aapka message admin tak pahunch gaya hai!")
        asyncio.create_task(delete_after_delay(confirmation))

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all replies"""
    if not update.message.reply_to_message:
        return

    ctx = load_context()
    replied_msg_id = str(update.message.reply_to_message.message_id)
    
    # Check if this is an admin reply
    if update.effective_user.id in ADMIN_ID:
        if replied_msg_id not in ctx:
            return  # Ignore admin replies to non-tracked messages
            
        if ctx[replied_msg_id].get('is_admin_copy'):
            # This is admin replying to forwarded message
            source_msg_id = ctx[replied_msg_id]['source_message_id']
            source_info = ctx.get(source_msg_id)
            
            if not source_info:
                return
                
            try:
                await context.bot.send_message(
                    chat_id=source_info['chat_id'],
                    text=update.message.text,
                    reply_to_message_id=source_info['original_msg_id']
                )
                confirmation = await update.message.reply_text("✅ Reply bhej diya gaya hai!")
                asyncio.create_task(delete_after_delay(confirmation))
                
                if LOG_CHANNEL:
                    await context.bot.send_message(
                        LOG_CHANNEL,
                        f"#Reply\nAdmin: {update.effective_user.full_name}\n"
                        f"To: {source_info['user_id']}\nMsg: {update.message.text}"
                    )
            except Exception as e:
                await update.message.reply_text(f"❌ Reply bhejne mein error aaya: {str(e)}")
        return
    
    # Handle user replies to bot messages
    if update.message.reply_to_message.from_user.id == context.bot.id:
        await handle_message(update, context)  # Process as new message

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reply command"""
    if update.effective_user.id not in ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        error_msg = await update.message.reply_text("Usage:\n/reply <user_id> <message>")
        asyncio.create_task(delete_after_delay(error_msg))
        return
    
    user_id = context.args[0]
    message = ' '.join(context.args[1:])
    
    try:
        await context.bot.send_message(user_id, message)
        confirmation = await update.message.reply_text("✅ Reply bhej diya gaya hai!")
        asyncio.create_task(delete_after_delay(confirmation))
        
        if LOG_CHANNEL:
            await context.bot.send_message(
                LOG_CHANNEL,
                f"#Reply\nAdmin: {update.effective_user.full_name}\n"
                f"To: {user_id}\nMsg: {message}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Reply bhejne mein error aaya: {str(e)}")

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /info command"""
    if update.effective_user.id not in ADMIN_ID:
        return
    
    if not update.message.reply_to_message:
        error_msg = await update.message.reply_text("⚠️ Kisi forwarded message pe /info reply karein")
        return
    
    ctx = load_context()
    replied_msg_id = str(update.message.reply_to_message.message_id)
    
    if replied_msg_id not in ctx:
        error_msg = await update.message.reply_text("⚠️ Is message ka context nahi mila")
        return
    
    user_id = ctx[replied_msg_id]['user_id']
    
    try:
        user = await context.bot.get_chat(user_id)
        # Create copy buttons
        keyboard = [
            [InlineKeyboardButton("Name Copy Karein", callback_data=f"copy_name_{user.full_name}")],
            [InlineKeyboardButton("Username Copy Karein", callback_data=f"copy_username_{user.username or 'None'}")],
            [InlineKeyboardButton("ID Copy Karein", callback_data=f"copy_id_{user.id}")]
        ]
        
        response = (
            f"👤 User Info:\n"
            f"Name: {user.full_name}\n"
            f"Username: @{user.username or 'None'}\n"
            f"ID: {user.id}\n\n"
            f"Copy karne ke liye niche click karein:"
        )
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"❌ User info fetch karne mein error aaya: {str(e)}")

async def handle_copy_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("copy_"):
        _, field, value = query.data.split("_", 2)
        await query.edit_message_text(f"✅ {field.capitalize()} copy ho gaya: {value}")

def get_message_handlers():
    return [
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID),
            handle_message
        ),
        MessageHandler(
            filters.TEXT & filters.REPLY,
            handle_reply
        ),
        CommandHandler("reply", admin_reply),
        CommandHandler("info", user_info),
        CallbackQueryHandler(handle_copy_button)
    ]
