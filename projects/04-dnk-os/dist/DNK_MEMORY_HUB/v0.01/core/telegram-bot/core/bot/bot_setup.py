import os
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

logger = logging.getLogger("BotSetup")

env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(dotenv_path=env_path)

bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "dummy_token_for_tests")
bot = Bot(token=bot_token)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🔱 *Привіт! Я — DNK Memory HUB.*\n"
        "Ваша центральна нервова система.\n\n"
        "Відправляйте мені нотатки, файли або посилання, і я збережу їх у Вашій базі (Wiki), а Гєрич (Агент) обробить їх у фоні.\n"
        "Команди:\n"
        "`/search <query>` - Пошук на GitHub",
        parse_mode="Markdown"
    )

@dp.message(Command("search"))
async def cmd_search(message: Message):
    query = message.text.replace("/search", "").strip()
    if not query:
        await message.answer("⚠️ Будь ласка, вкажіть запит, наприклад: `/search ai agents`", parse_mode="Markdown")
        return
        
    await message.answer(f"🔍 Запускаю аналіз GitHub для: *{query}*\n_Це може зайняти кілька хвилин..._", parse_mode="Markdown")
    
    try:
        from core.research_tools.git_core.search import search_repos
        from core.research_tools.git_core.analyzer import analyze_batch
        from core.research_tools.git_core.ranker import rank_repos
        
        # Виконуємо пошук
        loop = asyncio.get_event_loop()
        repos = await loop.run_in_executor(None, search_repos, query, 5) # Беремо топ-5
        
        if not repos:
            await message.answer("❌ Нічого не знайдено на GitHub.")
            return
            
        # Аналіз
        await message.answer(f"🤖 Знайдено {len(repos)} репозиторіїв. Починаю AI-аналіз...")
        repos = await loop.run_in_executor(None, analyze_batch, repos, True) # з README
        repos = rank_repos(repos)
        
        if not repos:
            await message.answer("❌ Помилка аналізу.")
            return
            
        best = repos[0]
        score = best.get("dnk_total_score", 0)
        
        response = f"✅ *Аналіз завершено для '{query}'*\n\n"
        response += f"🏆 *Топ результат:* [{best.get('full_name')}](https://github.com/{best.get('full_name')})\n"
        response += f"⭐ Stars: {best.get('stars')} | 🧬 Score: {score:.1f}/10\n\n"
        response += f"📝 *Резюме:* {best.get('summary_ua', '—')}\n\n"
        response += f"💡 *Рекомендація:* {best.get('recommendation', '—')}"
        
        await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in cmd_search: {e}")
        await message.answer(f"❌ Сталася помилка при пошуку: {e}")

@dp.message(F.text)
async def handle_text(message: Message):
    text = message.text
    
    message_id = str(uuid.uuid4())[:8]
    # Визначаємо шлях до глобального vault/raw
    # __file__ is core/telegram-bot/core/bot/bot_setup.py
    # нам треба піднятися на 4 рівні до DNK_HUB
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "memory", "vault", "raw"))
    os.makedirs(raw_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, f"msg_{message_id}.txt")
    
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(f"Source: Telegram\n")
        f.write(f"ChatId: {message.chat.id}\n")
        if message.message_thread_id:
            f.write(f"ThreadId: {message.message_thread_id}\n")
        f.write(f"User: {message.from_user.full_name}\n")
        f.write(f"Date: {message.date}\n")
        f.write(f"---\n")
        f.write(f"{text}\n")
    
    await message.answer(f"✅ Нотатку збережено в `raw/msg_{message_id}.txt`.\nАгент підхопить її найближчим часом.", parse_mode="Markdown")
