import asyncio
from datetime import datetime
from pytz import timezone
from recorder import start_recording
from typing import Dict, Optional

scheduled_jobs: Dict[int, asyncio.Task] = {}  # key = message_id, value = asyncio.Task

def get_ist_datetime(date_time_str: str) -> datetime:
    """Parse string datetime and convert to IST timezone"""
    ist = timezone("Asia/Kolkata")
    dt = datetime.strptime(date_time_str, "%d-%m-%Y %H:%M:%S")
    return ist.localize(dt)

async def start_recording_instantly(
    url: str, 
    duration: str, 
    channel: str, 
    title: str, 
    chat_id: int, 
    message_id: int
):
    """Start recording immediately"""
    task = asyncio.create_task(start_recording(url, duration, channel, title, chat_id, message_id))
    
    if message_id:
        scheduled_jobs[message_id] = task
    
    return task

async def schedule_recording(
    url: str,
    start_time_str: str,
    duration: str,
    channel: str,
    title: str,
    chat_id: int,
    message_id: Optional[int] = None
):
    """Schedule a recording for future time"""
    target_time = get_ist_datetime(start_time_str)
    current_time = datetime.now(timezone("Asia/Kolkata"))
    delay = (target_time - current_time).total_seconds()

    if delay < 0:
        print("Start time is in the past. Starting immediately.")
        delay = 0

    async def delayed_recording():
        if delay > 0:
            await asyncio.sleep(delay)
        await start_recording(url, duration, channel, title, chat_id)

    task = asyncio.create_task(delayed_recording())
    
    if message_id:
        scheduled_jobs[message_id] = task

    print(f"Recording scheduled at {target_time} IST for {duration}")
    return task

def cancel_scheduled_recording(message_id: int):
    """Cancel a scheduled recording by its message ID"""
    if message_id in scheduled_jobs:
        task = scheduled_jobs[message_id]
        task.cancel()
        del scheduled_jobs[message_id]
        return True
    return False
