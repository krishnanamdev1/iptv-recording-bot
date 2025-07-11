import os
import subprocess
import telebot
from datetime import datetime

# --- Configuration ---
BOT_TOKEN = "7999399648:AAFyaPONxQ9AlCoKr2a8U_U7UFd-Wuaq_ac"
bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@bot.message_handler(commands=["pastrecord"])
def handle_past_record(message):
    try:
        args = message.text.split(maxsplit=6)
        if len(args) < 6:
            return bot.reply_to(message, "❌ Usage:\n/pastrecord <m3u8_url> <date: YYYY-MM-DD> <start_time: HH:MM:SS> <duration: HH:MM:SS> <filename>")

        m3u8_url = args[1]
        date_str = args[2]
        start_time_str = args[3]
        duration = args[4]
        filename = args[5]

        # Optional: You can use date and time to calculate offset if playlist supports seeking
        timestamp = f"{date_str} {start_time_str}"
        try:
            datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return bot.reply_to(message, "❌ Invalid date or time format. Use YYYY-MM-DD and HH:MM:SS")

        output_file = os.path.join(DOWNLOAD_DIR, filename)

        command = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-headers", "User-Agent: Mozilla/5.0\r\nReferer: https://www.tataplay.com/\r\nOrigin: https://www.tataplay.com",
            "-i", m3u8_url,
            "-t", duration,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "96k",
            "-f", "matroska",
            output_file
        ]

        bot.reply_to(message, f"🎬 Recording started...\n📁 File: {filename}", parse_mode="Markdown")

        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if os.path.exists(output_file):
            with open(output_file, "rb") as f:
                bot.send_document(message.chat.id, f, caption=f"✅ Recording done: {filename}", parse_mode="Markdown")
            os.remove(output_file)
        else:
            bot.reply_to(message, "❌ Recording failed. File not found.")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error occurred: {str(e)}")

# --- Start Bot ---
print("🤖 Bot is running...")
bot.infinity_polling()