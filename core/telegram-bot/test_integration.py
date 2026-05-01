import asyncio
import os
import sys
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrationTest")

# Додаємо шлях до модулів
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_hermes():
    logger.info("--- Тестування Hermes Agent Integration ---")
    from core.agent_runner.hermes_wrapper import HermesAgentWrapper
    
    wrapper = HermesAgentWrapper(config_dir="config")
    
    # Створюємо тестовий файл
    test_file = "data/raw/test_note.txt"
    os.makedirs("data/raw", exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Це тестова нотатка для перевірки інтеграції DNK_Memory_HUB.")
    
    logger.info(f"Запуск Injest для {test_file}...")
    result = await wrapper.process_injest(test_file)
    logger.info(f"Результат від Агента:\n{result}")

async def test_git_research():
    logger.info("--- Тестування Git Research Integration ---")
    try:
        from core.research_tools.git_core.search import search_repos
        logger.info("Виконую пошук репозиторіїв 'ai agents'...")
        # Використовуємо маленьку кількість для тесту
        repos = search_repos("ai agents", max_results=2)
        logger.info(f"Знайдено репозиторіїв: {len(repos)}")
        for r in repos:
            logger.info(f"- {r.get('full_name')} (Stars: {r.get('stars')})")
    except Exception as e:
        logger.error(f"Помилка в Git Research: {e}")

async def main():
    # Завантажуємо змінні середовища
    from dotenv import load_dotenv
    load_dotenv("config/.env")
    
    await test_hermes()
    await test_git_research()
    logger.info("--- Тестування завершено ---")

if __name__ == "__main__":
    asyncio.run(main())
