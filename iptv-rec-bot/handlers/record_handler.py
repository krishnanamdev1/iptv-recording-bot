import time
import shlex
import asyncio
from datetime import timedelta, datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils.admin_checker import is_temp_admin
from scheduler import start_recording_instantly
from utils.logging import log_to_channel
from config import ADMIN_ID
from m3u_manager import m3u_manager
from telegram.ext import Application, CommandHandler, ContextTypes




async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """Splits long messages into chunks of 4096 characters."""
    max_length = 4096
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        await update.message.reply_text(chunk, parse_mode=parse_mode)

async def handle_instant_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_ID and not await is_temp_admin(user_id):
        await update.message.reply_text("⚠️ Unauthorized Access", parse_mode="Markdown")
        return

    try:
        # Parse command and extract playlist filter
        command = update.message.text.split()[0]  # /rec, /p1, /p2, etc.
        playlist_filter = None
        
        if command.startswith("/p") and command[2:].isdigit():
            playlist_filter = f"p{command[2:]}"
        
        # Parse arguments
        parts = shlex.split(update.message.text)
        if len(parts) < 3:
            await update.message.reply_text(
                "❗ *Usage:*\n"
                "`/rec <channel_id> <duration> [title]`\n"
                "`/p1 <channel_id> <duration> [title]`\n"
                "`/p2 <channel_id> <duration> [title]`\n"
                "Example: `/rec 666 20 test`",
                parse_mode="Markdown"
            )
            return

        identifier = parts[1]
        duration_str = parts[2]
        title = " ".join(parts[3:]) if len(parts) > 3 else "Untitled"
        chat_id = update.effective_chat.id

        # Parse duration
        try:
            if ":" in duration_str:
                time_parts = list(map(int, duration_str.split(":")))
                if len(time_parts) == 3:  # HH:MM:SS
                    duration_sec = time_parts[0]*3600 + time_parts[1]*60 + time_parts[2]
                elif len(time_parts) == 2:  # MM:SS
                    duration_sec = time_parts[0]*60 + time_parts[1]
                else:
                    raise ValueError("Invalid time format")
            else:
                duration_sec = int(duration_str)
            
            duration_display = str(timedelta(seconds=duration_sec))
        except (ValueError, TypeError) as e:
            await update.message.reply_text(
                "❌ *Invalid duration format!*\n"
                "Valid formats: 10, 00:10, 00:00:10",
                parse_mode="Markdown"
            )
            return

        # Get URL - handles both direct M3U8 links and channel identifiers
        if identifier.startswith(('http://', 'https://')):
            url = identifier
            channel_name = "Direct Stream"
        else:
            # Find channel with playlist filter
            channel_info = None
            if playlist_filter:
                # Search only in the specified playlist
                for channel_id, info in m3u_manager.channels.items():
                    if isinstance(channel_id, str) and ':' in channel_id:
                        if info.get('playlist') == playlist_filter and (
                            identifier.lower() == info['name'].lower() or
                            identifier.lower() == info.get('original_id', '').lower()
                        ):
                            channel_info = info
                            break
            else:
                # Search in all playlists
                channel_info = m3u_manager.get_channel_info(identifier)
            
            if not channel_info:
                # Try finding similar channels
                similar = m3u_manager.search_channels(identifier, playlist_filter)
                if similar:
                    response = "🔍 Similar channels found:\n" + "\n".join(
                        f"{info['name']} (ID: {info['original_id']})" 
                        for info in similar.values()
                    )
                    await send_long_message(update, response, parse_mode="Markdown")
                else:
                    await update.message.reply_text(
                        f"❌ Channel not found: {identifier}\n"
                        "Use /find to search channels",
                        parse_mode="Markdown"
                    )
                return
            url = channel_info['url']
            channel_name = channel_info.get('name', identifier)

        # Start recording
        message_id = update.message.message_id
        
        asyncio.create_task(start_recording_instantly(
            url, duration_display, channel_name, title, 
            chat_id, message_id
        ))
      #  log_to_channel(chat_id, message.from_user.username or "Unknown", message.text, start_time_str, title)
        

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        await send_long_message(update, error_msg, parse_mode="Markdown")


async def handle_find_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "❗ *Usage:*\n"
                "`/find <channel_name> [.p1|.p2|...]`\n"
                "Example: `/find dd news .p1`",
                parse_mode="Markdown"
            )
            return

        # Combine all arguments except playlist filter
        search_parts = []
        playlist_filter = None
        
        for arg in args:
            if arg.startswith('.'):
                playlist_filter = arg[1:]  # Remove the dot
            else:
                search_parts.append(arg.lower())
                
        search_query = ' '.join(search_parts)
        
        # Search channels with exact match first
        exact_results = {}
        partial_results = {}
        
        for channel_id, info in m3u_manager.channels.items():
            if isinstance(channel_id, str) and ':' in channel_id:  # Only real channels
                # Apply playlist filter if specified
                if playlist_filter and info.get('playlist') != f"p{playlist_filter}":
                    continue
                
                # Check for exact match
                channel_name = info['name'].lower()
                channel_id_lower = info.get('original_id', '').lower()
                
                if search_query == channel_name or search_query == channel_id_lower:
                    exact_results[channel_id] = info
                elif all(term in (channel_name + ' ' + channel_id_lower) 
                         for term in search_query.split()):
                    partial_results[channel_id] = info

        # Combine results (exact matches first)
        results = {**exact_results, **partial_results}

        if not results:
            await update.message.reply_text(
                "❌ No channels found matching your search",
                parse_mode="Markdown"
            )
            return

        # Group results by playlist and paginate
        grouped_results = {}
        for channel_id, info in results.items():
            playlist_id = info['playlist']
            if playlist_id not in grouped_results:
                grouped_results[playlist_id] = []
            grouped_results[playlist_id].append(
                f"{info['name']} (ID: {info['original_id']})"
            )

        # Send results with pagination (max 10 items per message)
        for playlist_id, channels in grouped_results.items():
            header = f"📡 *Playlist {playlist_id.upper()}* ({len(channels)} results)\n"
            message = header
            
            for i, channel in enumerate(channels, 1):
                if i % 10 == 0:  # Send every 10 channels
                    await update.message.reply_text(
                        message,
                        parse_mode="Markdown"
                    )
                    message = header
                message += f"{channel}\n"
            
            if message != header:  # Send remaining channels
                await update.message.reply_text(
                    message,
                    parse_mode="Markdown"
                )

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        await send_long_message(update, error_msg, parse_mode="Markdown")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📝 *Usage:*\n\n"
        "• By URL:\n`/rec http://example.com/stream 30 channel title`\n"
        "• By Channel ID:\n`/rec 123 00:01:00 channel title`\n"
        "• By Channel Name:\n`/rec sony 1:00:00 channel title`\n\n"
        "⏱ *Duration formats:*\n"
        "`30` (seconds)\n`1:30` (minutes:seconds)\n`1:00:00` (hours:minutes:seconds)\n\n"
        "🔍 Search channels with `/find name`"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

