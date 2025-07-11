import os
import asyncio
from typing import Optional, List, Dict
from pyrogram import Client
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, SESSION_NAME, STORE_CHANNEL_ID
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


    def upload_progress_callback(self, current: int, total: int):
        percent = current * 100 / total
        uploaded = current / 1024 / 1024
        total_mb = total / 1024 / 1024
        print(f"Uploading: {uploaded:.2f}MB / {total_mb:.2f}MB ({percent:.2f}%)")
        # Jo print Hai vah raha hai iska ek progress bar banaa kar bot message mein dikhana hai progress chalti Hui dikhaiye aur pura code perfect hai kuchh changes nahin karni

    async def send_video(self, file_path: str, caption: str, thumbnail: Optional[str] = None, duration: Optional[int] = None) -> Optional[int]:
        async with self._lock:
            try:
                file_size = os.path.getsize(file_path)
                MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

                if file_size > MAX_SIZE:
                    print(f"[Error] File too large: {file_path}")
                    return None

                async with Client(
                    name=SESSION_NAME,
                    api_id=API_ID,
                    api_hash=API_HASH,
                    workdir=self.session_dir
                ) as app:

                    thumb = thumbnail if thumbnail and os.path.exists(thumbnail) else None

                    message = await app.send_video(
                        chat_id=STORE_CHANNEL_ID,
                        video=file_path,
                        caption=caption,
                        thumb=thumb,
                        progress=self.upload_progress_callback,
                        duration=duration  # ✅ Added duration parameter
                    )

                    print(f"[Uploaded] {file_path} -> Message ID: {message.id}")
                    return message.id

            except FloodWait as e:
                print(f"[FloodWait] Sleeping for {e.value} seconds...")
                await asyncio.sleep(e.value)
                return await self.send_video(file_path, caption, thumbnail)
            except Exception as e:
                print(f"[Upload Error] {str(e)}")
                return None

    async def upload_sequence(self, video_list: List[Dict[str, str]]) -> List[int]:
        results = []
        for video in video_list:
            print(f"\n[Uploading] {video['path']}")
            msg_id = await self.send_video(
                file_path=video['path'],
                caption=video.get('caption', ''),
                thumbnail=video.get('thumbnail')
            )
            if msg_id:
                results.append(msg_id)
            else:
                print(f"[Failed] {video['path']}")
        return results


# Public interfaces
upload_manager = UploadManager()

async def send_video(file_path: str, caption: str, thumbnail: Optional[str] = None, duration: Optional[int] = None) -> Optional[int]:
    return await upload_manager.send_video(file_path, caption, thumbnail, duration)

async def upload_videos(video_list: List[Dict[str, str]]) -> List[int]:
    return await upload_manager.upload_sequence(video_list)


# For testing (CLI)
if __name__ == "__main__":
    async def test_upload():
        videos = [
            {'path': 'video1.mp4', 'caption': 'First Video', 'duration': 10},
            {'path': 'video2.mp4', 'caption': 'Second Video', 'duration': 15}
        ]
        await upload_videos(videos)

    asyncio.run(test_upload())
