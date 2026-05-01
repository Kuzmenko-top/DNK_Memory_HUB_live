"""
migrate_existing_repos.py — Міграція JSON бібліотеки → PostgreSQL
Використання: python scripts/migrate_existing_repos.py
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from loguru import logger
from src.storage import load_library
from core.database import save_repo, is_available


def run_migration() -> None:
    if not is_available():
        logger.error("❌ PostgreSQL недоступний. Перевір POSTGRES_URL у .env")
        logger.info("💡 Для локального запуску: docker run -e POSTGRES_PASSWORD=postgres "
                    "-e POSTGRES_DB=dnk_git -p 5432:5432 ankane/pgvector")
        sys.exit(1)

    lib = load_library()
    repos = list(lib.get("repos", {}).values())
    total = len(repos)

    if total == 0:
        logger.warning("⚠️ Бібліотека порожня — нічого мігрувати")
        return

    logger.info(f"🚀 Починаємо міграцію {total} репозиторіїв...")
    success, failed = 0, 0

    for i, repo in enumerate(repos, 1):
        name = repo.get("full_name", repo.get("name", "?"))
        repo_id = save_repo(repo)
        if repo_id:
            success += 1
            if i % 50 == 0 or i == total:
                logger.info(f"[{i}/{total}] ✅ {name}")
        else:
            failed += 1
            logger.warning(f"[{i}/{total}] ❌ Не вдалось: {name}")

    logger.success(f"\n✅ Міграцію завершено: {success} успішно, {failed} помилок з {total} репо")


if __name__ == "__main__":
    run_migration()
