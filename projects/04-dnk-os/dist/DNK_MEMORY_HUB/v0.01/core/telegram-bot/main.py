import asyncio
import logging
from dotenv import load_dotenv
import os
import sys

# Додаємо поточну директорію в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.bot.bot_setup import dp, bot

def setup_env():
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), "config", ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        print(f"Warning: .env file not found at {env_path}")

async def main():
    setup_env()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logger = logging.getLogger("HUB_MAIN")
    logger.info("Starting DNK_Memory_HUB Bot...")
    
    from core.memory_manager.worker import start_background_worker
    
    # Start background worker concurrently
    asyncio.create_task(start_background_worker())
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
