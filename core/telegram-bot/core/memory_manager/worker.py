import asyncio
import os
import logging
from core.agent_runner.multi_agent import multi_agent_manager
from core.bot.bot_setup import bot
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("BackgroundWorker")

HUB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# Визначаємо корінь всього проекту DNK_HUB
DNK_HUB_ROOT = os.path.abspath(os.path.join(HUB_ROOT, "..", ".."))

# Глобальний Vault (база знань)
GLOBAL_VAULT = os.path.join(DNK_HUB_ROOT, "memory", "vault")

RAW_DIR = os.path.join(GLOBAL_VAULT, "raw")
CONFIG_DIR = os.path.join(HUB_ROOT, "config")
PROCESSED_DIR = os.path.join(GLOBAL_VAULT, "_archive", "processed_raw")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

async def check_raw_directory():
    try:
        files = os.listdir(RAW_DIR)
        for filename in files:
            file_path = os.path.join(RAW_DIR, filename)
            if os.path.isfile(file_path):
                logger.info(f"Found new file: {filename}")
                
                chat_id = ADMIN_ID
                thread_id = None
                content = ""
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        is_content = False
                        for line in lines:
                            if not is_content:
                                if line.startswith("ChatId: "):
                                    chat_id = line.replace("ChatId: ", "").strip()
                                elif line.startswith("ThreadId: "):
                                    thread_id = line.replace("ThreadId: ", "").strip()
                                elif line.startswith("---"):
                                    is_content = True
                            else:
                                content += line
                except Exception as e:
                    logger.error(f"Error parsing metadata from {filename}: {e}")

                # Формуємо промпт для Гєрича
                prompt = (
                    f"Команда: Injest\n"
                    f"Файл: {file_path}\n"
                    f"Контент:\n---\n{content}\n---\n"
                    f"Будь ласка, оброби цей файл згідно з нашою Schema.md. "
                    f"Якщо запит стосується іншої сфери, використовуй інструмент delegate_to_expert. "
                    f"Визнач куди його занести в wiki/ та які cross-links додати. Дай коротке резюме."
                )

                # Запускаємо головного агента (Бібліотекаря)
                result = await multi_agent_manager.process_with_agent("herich-librarian", prompt, chat_id)
                
                # Відправляємо результат в Telegram
                if chat_id:
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            message_thread_id=thread_id,
                            text=f"🤖 *Агент (Гєрич) обробив Ваше повідомлення:*\n\n{result}",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send message to {chat_id}: {e}")
                
                # Переміщуємо в архів
                os.rename(file_path, os.path.join(PROCESSED_DIR, filename))
                logger.info(f"File {filename} moved to processed archive.")
                
    except Exception as e:
        logger.error(f"Error in background worker: {e}")

async def start_background_worker(interval_seconds=10):
    logger.info("Background worker started. Watching data/raw/...")
    while True:
        await check_raw_directory()
        await asyncio.sleep(interval_seconds)
