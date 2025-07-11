from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN
import sys
import logging
import warnings

# Configure logging and warnings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Suppress unwanted logs
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('pyrogram').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def escape_markdown(text):
    """Escape special Markdown characters"""
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join('\\' + char if char in escape_chars else char for char in text)

def main():
    """Main synchronous bot function"""
    try:
        logger.info("Initializing bot...")
        
        # Build application
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .concurrent_updates(True)
            .build()
        )
        
        # Register handlers
        from handler import register_handlers
        register_handlers(application)
        
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Run polling
        application.run_polling(
            close_loop=False,
            stop_signals=None,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {escape_markdown(str(e))}")
    finally:
        logger.info("Clean shutdown complete")

if __name__ == "__main__":
    main()
