#!/usr/bin/env python3
"""
batch_analyze.py — пакетний аналіз репо з library.json → Qdrant.
Бере вже збережені репо і re-аналізує їх новим промптом (функціональний паспорт).

Використання:
  python3 batch_analyze.py --limit 50           # аналіз 50 репо
  python3 batch_analyze.py --limit 10 --dry-run # без запису
  python3 batch_analyze.py --reembed-only       # тільки перезаписати Qdrant (без AI)
"""
from __future__ import annotations
import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="DNK Git Research — batch analyze")
    parser.add_argument("--limit", type=int, default=20, help="Кількість репо для аналізу")
    parser.add_argument("--dry-run", action="store_true", help="Без збереження")
    parser.add_argument("--reembed-only", action="store_true", help="Тільки Qdrant upsert (без AI)")
    parser.add_argument("--skip-analyzed", action="store_true", default=True,
                        help="Пропустити репо які вже мають what_it_does (default: True)")
    parser.add_argument("--no-skip", dest="skip_analyzed", action="store_false")
    args = parser.parse_args()

    from src.storage import load_library, save_to_library, save_to_qdrant
    from src.analyzer import analyze_repo

    library = load_library()
    all_repos = list(library.get("repos", {}).values())
    logger.info(f"📚 Бібліотека: {len(all_repos)} репо")

    if args.reembed_only:
        logger.info("🔄 Режим re-embed: записуємо поточну бібліотеку в Qdrant...")
        batch = all_repos[:args.limit]
        if not args.dry_run:
            save_to_qdrant(batch)
        logger.success(f"✅ Re-embed завершено: {len(batch)} репо")
        return

    # Фільтруємо: тільки ті що ще не мають нового паспорта
    if args.skip_analyzed:
        queue = [r for r in all_repos if not r.get("what_it_does")]
        logger.info(f"🔍 Без паспорта: {len(queue)} репо (з {len(all_repos)} загалом)")
    else:
        queue = all_repos

    queue = queue[:args.limit]
    if not queue:
        logger.success("✅ Всі репо вже мають функціональний паспорт!")
        return

    logger.info(f"🤖 AI-аналіз {len(queue)} репо...")
    updated = []
    for i, repo in enumerate(queue, 1):
        name = repo.get("full_name", repo.get("name", "?"))
        logger.info(f"[{i}/{len(queue)}] {name}")
        try:
            analysis = analyze_repo(repo)
            repo.update(analysis)
            updated.append(repo)
            logger.success(f"  ✅ {name}: {(repo.get('what_it_does') or '')[:60]}")
        except Exception as e:
            logger.error(f"  ❌ {name}: {e}")

    if updated and not args.dry_run:
        save_to_library(updated)
        logger.success(f"\n✅ Збережено {len(updated)} репо (JSON + Qdrant)")
    elif args.dry_run:
        logger.info(f"\n[dry-run] Проаналізовано {len(updated)}, нічого не збережено")


if __name__ == "__main__":
    main()
