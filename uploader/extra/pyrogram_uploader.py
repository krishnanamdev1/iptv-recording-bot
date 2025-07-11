import os
import asyncio
from typing import Optional, List, Dict
from pyrogram import Client
from pyrogram.errors import FloodWait
from telegram import Bot, Message
from config import API_ID, API_HASH, SESSION_NAME, STORE_CHANNEL_ID, BOT_TOKEN
from captions import caption_uploaded

class UploadManager:
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        cls.session_dir = "session_files"
        os.makedirs(cls.session_dir, exist_ok=True)

    def __init__(self):
        if not hasattr(self, 'bot'):
            self.bot = Bot(token=BOT_TOKEN)
            self.progress_data = {}  # {chat_id: {'msg_id': int, 'user_msg_id': int, 'file': str}}
            self.last_update = {}
            self.loop = asyncio.get_event_loop()

    def upload_progress_callback(self, current: int, total: int, chat_id: int, file_name: str):
        """Wrapper to safely call async progress updates from sync context"""
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                self.async_upload_progress_callback(current, total, chat_id, file_name)
            )
        )

    async def async_upload_progress_callback(self, current: int, total: int, chat_id: int, file_name: str):
        """Enhanced progress callback with better error handling"""
        current_time = asyncio.get_event_loop().time()
        
        # Throttle updates to every 2 seconds
        if chat_id in self.last_update and current_time - self.last_update[chat_id] < 2:
            return
        
        self.last_update[chat_id] = current_time
        percent = min(100, (current / total) * 100)
        uploaded_mb = current / 1024 / 1024
        total_mb = total / 1024 / 1024

        # Visual progress bar
        bar = '⬢' * int(percent/5) + '⬡' * (20 - int(percent/5))
        
        progress_text = (
            f"*📤 Uploading:* `{file_name}`\n"
            f"*📊 Progress:* {percent:.1f}%\n"
            f"🔹 {uploaded_mb:.1f}MB / {total_mb:.1f}MB\n"
            f"{bar}\n"
            f"*⚡ Status:* Uploading..."
        )

        try:
            if chat_id not in self.progress_data:
              #  message_id = update.message.message_id
                # First progress update - send new message
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=progress_text,
                    reply_to_message_id=self.progress_data.get(chat_id, {}).get('user_msg_id'),
                    parse_mode="Markdown",
                 #   reply_to_message_id=message_id
                )
                self.progress_data[chat_id] = {
                    'msg_id': message.message_id,
                    'user_msg_id': self.progress_data.get(chat_id, {}).get('user_msg_id'),
                    'file': file_name
                }
            else:
                # Subsequent updates - edit existing message
                try:
                    await self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=self.progress_data[chat_id]['msg_id'],
                        text=progress_text,
                        parse_mode="Markdown"
                    )
                except Exception as edit_err:
                    # If edit fails, send new message and update reference
                    print(f"Progress edit failed, sending new: {edit_err}")
                    new_msg = await self.bot.send_message(
                        chat_id=chat_id,
                        text=progress_text,
                        reply_to_message_id=self.progress_data[chat_id]['user_msg_id'],
                        parse_mode="Markdown"
                    )
                    self.progress_data[chat_id]['msg_id'] = new_msg.message_id
        except Exception as e:
            print(f"Progress update failed: {e}")

    async def send_uploaded_message(self, chat_id: int, file_name: str, success: bool = True, error_msg: str = None):
        """Enhanced final message with better formatting"""
        try:
            if chat_id not in self.progress_data:
                return

            if success:
                final_text = (
                    f"📂 *File:* `{file_name}`\n"
                    "✅ *Uploaded Successfully!*\n"
                    "🎉 *Status:* Completed"
                ).format(file_name=file_name)
            else:
                final_text = (
                    f"📂 *File:* `{file_name}`\n"
                    "❌ *Upload Failed!*\n"
                    f"⚠️ *Reason:* {error_msg or 'Unknown error'}"
                ).format(file_name=file_name, error_msg=error_msg or 'Unknown error')

            try:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=self.progress_data[chat_id]['msg_id'],
                    text=final_text,
                    parse_mode="Markdown" 
                )
            except Exception as edit_err:
                # If edit fails, send new final message
                print(f"Final message edit failed: {edit_err}")
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=final_text,
                    reply_to_message_id=self.progress_data[chat_id]['user_msg_id'],
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Final message error: {e}")
        finally:
            # Clean up tracking data
            self.progress_data.pop(chat_id, None)
            self.last_update.pop(chat_id, None)
            
            
            

            
            
            

    async def send_video_pyrogram(self, file_path: str, caption: str, thumbnail: Optional[str] = None, 
                                duration: Optional[int] = None, chat_id: int = 0, 
                                user_msg_id: int = None) -> Optional[int]:
        """Core upload function with all requested improvements"""
        async with self._lock:
            try:
                # Initialize progress tracking
                self.progress_data[chat_id] = {
                    'msg_id': None,
                    'user_msg_id': user_msg_id,
                    'file': os.path.basename(file_path)
                }

                # Check file existence and size
                if not os.path.exists(file_path):
                    await self.send_uploaded_message(chat_id, os.path.basename(file_path), False, "File not found")
                    return None

                file_size = os.path.getsize(file_path)
                if file_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
                    await self.send_uploaded_message(chat_id, os.path.basename(file_path), False, "File too large (>2GB)")
                    return None

                async with Client(
                    name=SESSION_NAME,
                    api_id=API_ID,
                    api_hash=API_HASH,
                    workdir=self.session_dir
                ) as app:
                    # Upload with progress tracking
                    message = await app.send_video(
                        chat_id=STORE_CHANNEL_ID,
                        video=file_path,
                        caption=caption,
                        thumb=thumbnail if thumbnail and os.path.exists(thumbnail) else None,
                        progress=lambda curr, tot: self.upload_progress_callback(curr, tot, chat_id, os.path.basename(file_path)),
                        duration=duration,
                        reply_to_message_id=user_msg_id
                    )
                    
                    await self.send_uploaded_message(chat_id, os.path.basename(file_path), True)
                    return message.id

            except FloodWait as e:
                # Handle flood waits properly
                wait_msg = await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏳ Flood wait: Sleeping for {e.value} seconds...",
                    reply_to_message_id=user_msg_id
                )
                await asyncio.sleep(e.value)
                await self.bot.delete_message(chat_id, wait_msg.message_id)
                return await self.send_video_pyrogram(file_path, caption, thumbnail, duration, chat_id, user_msg_id)
                
            except Exception as e:
                error_msg = str(e).replace(BOT_TOKEN, "***")  # Redact bot token
                await self.send_uploaded_message(chat_id, os.path.basename(file_path), False, error_msg)
                return None

    async def upload_sequence(self, video_list: List[Dict[str, str]], chat_id: int, user_msg_id: int) -> List[int]:
        """Process multiple videos in sequence"""
        results = []
        for video in video_list:
            print(f"\n[Uploading] {video.get('path')}")
            msg_id = await self.send_video_pyrogram(
                file_path=video.get('path'),
                caption=video.get('caption', ''),
                thumbnail=video.get('thumbnail'),
                chat_id=chat_id,
                user_msg_id=user_msg_id
            )
            if msg_id:
                results.append(msg_id)
            else:
                print(f"[Failed] {video.get('path')}")
        return results

# Public interfaces
upload_manager = UploadManager()

async def send_video_pyrogram(file_path: str, caption: str, thumbnail: Optional[str] = None, 
                            duration: Optional[int] = None, chat_id: int = 0, 
                            user_msg_id: int = None) -> Optional[int]:
    """Public interface for single video upload"""
    return await upload_manager.send_video_pyrogram(
        file_path=file_path,
        caption=caption,
        thumbnail=thumbnail,
        duration=duration,
        chat_id=chat_id,
        user_msg_id=user_msg_id
    )

async def upload_videos(video_list: List[Dict[str, str]], chat_id: int, user_msg_id: int) -> List[int]:
    """Public interface for batch upload"""
    return await upload_manager.upload_sequence(video_list, chat_id, user_msg_id)
