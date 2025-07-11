from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
import random

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Help / Contact Developer", url="https://t.me/Requestadminuser_bot")],
        [InlineKeyboardButton("Request Admin Access", callback_data="request_admin")]
    ])
    
    welcome_text = f"**Welcome {user.first_name}**\n\nThis bot helps you record IPTV with ease."
    
    try:
        # Try random images first
        image_files = [f'assets/recording{i}.jpg' for i in range(1, 11)]  # recording1.jpg to recording10.jpg
        random.shuffle(image_files)
        sent = False
        
        for image_file in image_files:
            try:
                with open(image_file, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=welcome_text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    sent = True
                    break
            except FileNotFoundError:
                continue
            except Exception as photo_error:
                print(f"Error sending photo {image_file}: {photo_error}")
                continue
        
        # Fallback to text if no images worked
        if not sent:
            await update.message.reply_text(
                text=welcome_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
                
    except Exception as e:
        print(f"Error in start handler: {e}")
        # Final fallback
        await update.message.reply_text(
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
