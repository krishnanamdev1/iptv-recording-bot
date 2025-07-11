import os
import subprocess
import asyncio
import time
from datetime import datetime, timedelta
from pytz import timezone
import aiohttp
from config import RECORDINGS_DIR, BOT_TOKEN, STORE_CHANNEL_ID
from utils.utils import format_bytes, format_duration
from uploader.pyrogram_uploader import send_video_pyrogram
from telegram import Bot, error
from recorders.recorder_utils import resolve_stream, get_stream_quality
from features.status_broadcast import add_active_recording, remove_active_recording
import re

def create_progress_bar(progress, length=10):
    done = int(progress * length)
    left = length - done
    return f"[{'█' * done}{'░' * left}]"

def seconds_to_hms(seconds):
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def caption_recording_started(title, channel, duration_sec, start_time_str):
    duration_hms = seconds_to_hms(duration_sec)
    return (
        f"🎬 *Recording Started*\n\n"
        f"📌 *Title:* `{title}`\n"
        f"📺 *Channel:* `{channel}`\n"
        f"⏱ *Duration:* `{duration_hms}`\n"
        f"⏰ *Started At:* `{start_time_str}`\n\n"
        f"🔄 *Status:* Preparing to record..."
    )

def caption_recording_progress(title, channel, total_duration, start_time_str, elapsed_sec, remaining_sec, error_msg=None):
    progress = min(elapsed_sec / total_duration, 1)
    progress_bar = create_progress_bar(progress)
    
    elapsed_hms = seconds_to_hms(elapsed_sec)
    remaining_hms = seconds_to_hms(remaining_sec)
    total_hms = seconds_to_hms(total_duration)
    
    status = "❌ Failed" if error_msg else "🔄 Recording..."
    error_line = f"\n❗ *Error:* `{error_msg}`" if error_msg else ""
    
    return (
        f"⏳ *Recording in Progress*\n\n"
        f"📌 *Title:* `{title}`\n"
        f"📺 *Channel:* `{channel}`\n"
        f"⏱ *Duration:* `{total_hms}`\n"
        f"⏰ *Started At:* `{start_time_str}`\n\n"
        f"[{progress_bar}] {progress * 100:.1f}%\n"  # Added percentage here
        f"▶️ *Elapsed:* `{elapsed_hms}`\n"
        f"⏭ *Remaining:* `{remaining_hms}`\n\n"
        f"*Status:* {status}{error_line}"
    )


def caption_recording_completed(title, channel, duration_sec, start_time_str):
    duration_hms = seconds_to_hms(duration_sec)
    end_time_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return (
        f"✅ *Recording Completed*\n\n"
        f"📌 *Title:* `{title}`\n"
        f"📺 *Channel:* `{channel}`\n"
        f"⏱ *Duration:* `{duration_hms}`\n"
        f"⏰ *Started At:* `{start_time_str}`\n"
        f"🕒 *Ended At:* `{end_time_str}`\n\n"
        f"📤 *Status:* Preparing for upload..."
    )




async def start_recording(url: str, duration: str, channel: str, title: str, chat_id: int, message_id: int):
    bot = Bot(token=BOT_TOKEN)
    recording_message = None
    last_caption = ""
    process = None
    start_ts = time.time()
    error_occurred = False
    
    try:
        ist = timezone("Asia/Kolkata")
        now = datetime.now(ist)

        try:
            if ":" in duration:
                h, m, s = map(int, duration.split(":"))
                total_seconds = h * 3600 + m * 60 + s
            else:
                total_seconds = int(duration)
        except ValueError:
            await bot.send_message(chat_id, "⚠️ Invalid duration format. Use HH:MM:SS.")
            return
        
        end_ts = start_ts + total_seconds
        end_time = now + timedelta(seconds=total_seconds)
        start_time_str = now.strftime("%d-%m-%Y %H:%M:%S")

        initial_caption = caption_recording_started(title, channel, total_seconds, start_time_str)
        last_caption = initial_caption
        
        # Modified part - directly send text message without image
        try:
            recording_message = await bot.send_message(
                chat_id=chat_id,
                text=initial_caption,
                parse_mode="Markdown",
                reply_to_message_id=message_id
            )
        except Exception as e:
            print(f"Error sending recording notification: {e}")
            recording_message = await bot.send_message(
                chat_id=chat_id,
                text=initial_caption,
                parse_mode="Markdown",
                reply_to_message_id=message_id
            )

        async def update_caption(caption_text):
            nonlocal last_caption
            if caption_text != last_caption:
                try:
                    await bot.edit_message_text(
                        text=caption_text,
                        chat_id=chat_id,
                        message_id=recording_message.message_id,
                        parse_mode="Markdown",
                    )
                    last_caption = caption_text
                except Exception as e:
                    print(f"Error updating caption: {e}")

        async def update_progress_bar():
            nonlocal last_caption, process, start_ts, error_occurred  # Modified here
            end_ts = start_ts + total_seconds
            last_update_time = start_ts  # Track last update time

            while time.time() < end_ts:
                current_time = time.time()
                elapsed = current_time - start_ts
                time_left = max(0, end_ts - current_time)
                
                # Update every 1 second instead of 5
                if current_time - last_update_time >= 1:  # Faster updates
                    caption_text = caption_recording_progress(
                        title, channel, total_seconds, start_time_str,
                        elapsed, time_left
                    )
                    await update_caption(caption_text)
                    last_update_time = current_time
                    
                await asyncio.sleep(3)  # Reduced sleep time

                if process and process.returncode is not None and process.returncode != 0:
                    if not error_occurred:
                        stderr = await process.stderr.read() if process.stderr else b'Unknown error'
                        error_msg = stderr.decode().strip()[:100]
                        caption_text = caption_recording_progress(
                            title, channel, total_seconds, start_time_str,
                            elapsed, time_left, error_msg
                        )
                        await update_caption(caption_text)
                        error_occurred = True
                    return

            # Immediately after loop ends (recording complete)
            final_caption = caption_recording_completed(title, channel, total_seconds, start_time_str)
            await update_caption(final_caption)
            
            # Wait for process to finish completely
            if process and process.returncode is None:
                await process.wait()

        progress_task = asyncio.create_task(update_progress_bar())

        temp_filename = f"temp_recording_{now.timestamp()}.mkv"
        temp_path = os.path.join(RECORDINGS_DIR, temp_filename)
        os.makedirs(RECORDINGS_DIR, exist_ok=True)

        print(f"[Recorder] Starting recording...")
        stream_url = await resolve_stream(url)
        # Add this where you start the recording
        recording_id = add_active_recording({
            'title': title,
            'channel': channel,
            'duration': total_seconds,
            'user_id': chat_id
        })


        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-headers", f"User-Agent: Mozilla/5.0\r\nReferer: https://www.tataplay.com/\r\nOrigin: https://www.tataplay.com",
            "-i", stream_url,
            "-t", duration,
            "-map", "0:v?",
            "-map", "0:a?",
            "-map", "0:s?",
            "-c", "copy",
            temp_path
        ]

        process = await asyncio.create_subprocess_exec(*cmd)
        return_code = await process.wait()
        await progress_task  # Ensure progress bar completes

        if return_code != 0:
            if not error_occurred:
                error_msg = "❌ Recording failed (FFmpeg error)"
                caption_text = caption_recording_progress(
                    title, channel, total_seconds, start_time_str,
                    time.time() - start_ts, end_ts - time.time(),
                    error_msg
                )
                await update_caption(caption_text)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return

        sanitized_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        sanitized_channel = re.sub(r'[<>:"/\\|?*]', '_', channel)
        
        time_format = "%H-%M-%S"
        
        final_filename = f"{sanitized_title}.{sanitized_channel}.{now.strftime(time_format)}-{end_time.strftime(time_format)}.{now.strftime('%d-%m-%Y')}.IPTV.WEB-DL.@Krinry.mkv"
        output_path = os.path.join(RECORDINGS_DIR, final_filename)
        os.rename(temp_path, output_path)

        thumbnail_path = os.path.join(RECORDINGS_DIR, f"{final_filename}.jpg")
        thumbnail_cmd = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-i", output_path,
            "-ss", "00:00:01",
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale=320:-1",
            thumbnail_path
        ]
        await (await asyncio.create_subprocess_exec(*thumbnail_cmd)).wait()

        readable_duration = await format_duration(duration)
        readable_size = await format_bytes(os.path.getsize(output_path))

        caption = f"""`📁 Filename: {final_filename}
⏱ Duration: {readable_duration}
💾 File-Size: {readable_size}`
☎️ @Requestadminuser_bot"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                new_message_id = await send_video_pyrogram(
                    output_path, 
                    caption, 
                    thumbnail=thumbnail_path, 
                    duration=int(total_seconds), 
                    chat_id=chat_id,
                )
                if new_message_id:
                    await bot.copy_message(chat_id=chat_id, from_chat_id=STORE_CHANNEL_ID, message_id=new_message_id)
                    remove_active_recording(recording_id)
                    break
            except Exception as upload_error:
                if attempt == max_retries - 1:
                    error_msg = f"❌ Upload failed: {str(upload_error)}"
                    caption_text = caption_recording_progress(
                        title, channel, total_seconds, start_time_str,
                        time.time() - start_ts, end_ts - time.time(),
                        error_msg
                    )
                    await update_caption(caption_text)
                await asyncio.sleep(5)

        try:
            os.remove(output_path)
            os.remove(thumbnail_path)
        except Exception as e:
            print(f"Error cleaning up files: {e}")
        # Add this when recording finishes (both success and error cases)
        


    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        if recording_message and 'start_ts' in locals() and 'total_seconds' in locals():
            caption_text = caption_recording_progress(
                title, channel, total_seconds, start_time_str,
                time.time() - start_ts, end_ts - time.time(),
                error_msg
            )
            
            await update_caption(caption_text)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
