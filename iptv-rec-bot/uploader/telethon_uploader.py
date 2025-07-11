import os
import asyncio
from typing import Optional, List, Dict
from telethon.sync import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from config import API_ID, API_HASH, BOT_TOKEN, STORE_CHANNEL_ID
from captions import caption_uploaded


class TelethonUploader:
    def __init__(self):
        self.client = TelegramClient('telethon_bot', API_ID, API_HASH)
        self.lock = asyncio.Lock()

    async def upload_progress(self, current, total):
        percent = current * 100 / total
        uploaded = current / 1024 / 1024
        total_mb = total / 1024 / 1024
        print(f"Uploading: {uploaded:.2f}MB / {total_mb:.2f}MB ({percent:.2f}%)")

    async def send_video_telethon(self, file_path: str, caption: str, thumbnail: Optional[str] = None, duration: Optional[int] = None) -> Optional[int]:
        async with self.lock:
            try:
                file_size = os.path.getsize(file_path)
                MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

                if file_size > MAX_SIZE:
                    print(f"[Error] File too large: {file_path}")
                    return None

                await self.client.start(bot_token=BOT_TOKEN)

                thumb = thumbnail if thumbnail and os.path.exists(thumbnail) else None

                result = await self.client.upload_file(
                    file=file_path,
                    progress_callback=self.upload_progress
                )

                entity = await self.client.get_entity(STORE_CHANNEL_ID)

                message = await self.client.send_message(
                    entity=entity,
                    message=caption,
                    file=result,
                    attributes=[
                        DocumentAttributeVideo(
                            duration=duration or 0,
                            w=0,
                            h=0,
                            supports_streaming=True
                        )
                    ],
                    thumb=thumb
                )

                print(f"[Uploaded] {file_path} -> Message ID: {message.id}")
                return message.id

            except Exception as e:
                print(f"[Upload Error] {str(e)}")
                return None

    async def upload_sequence(self, video_list: List[Dict[str, str]]) -> List[int]:
        results = []
        for video in video_list:
            print(f"\n[Uploading] {video['path']}")
            msg_id = await self.send_video_telethon(
                file_path=video['path'],
                caption=video.get('caption', ''),
                thumbnail=video.get('thumbnail'),
                duration=video.get('duration')
            )
            if msg_id:
                results.append(msg_id)
            else:
                print(f"[Failed] {video['path']}")
        return results


# Public interfaces
telethon_uploader = TelethonUploader()


async def send_video_telethon(file_path: str, caption: str, thumbnail: Optional[str] = None, duration: Optional[int] = None) -> Optional[int]:
    return await telethon_uploader.send_video_telethon(file_path, caption, thumbnail, duration)


async def upload_videos(video_list: List[Dict[str, str]]) -> List[int]:
    return await telethon_uploader.upload_sequence(video_list)


# For testing (CLI)
if __name__ == "__main__":
    async def test_upload():
        videos = [
            {'path': 'video1.mkv', 'caption': 'First Video', 'duration': 10},
            {'path': 'video2.mkv', 'caption': 'Second Video', 'duration': 15}
        ]
        await upload_videos(videos)

    asyncio.run(test_upload())
