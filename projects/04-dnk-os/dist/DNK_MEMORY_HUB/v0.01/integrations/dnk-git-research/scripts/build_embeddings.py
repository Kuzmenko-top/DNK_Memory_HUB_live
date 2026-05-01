"""
build_embeddings.py — Заповнити таблицю embeddings для всіх репо в DB
Використання: python scripts/build_embeddings.py [--rebuild]
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from core.database import _get_conn, is_available
from core.embeddings import embed_text, build_repo_text, save_embedding


def run(rebuild: bool = False) -> None:
    if not is_available():
        logger.error("❌ PostgreSQL недоступний")
        sys.exit(1)

    conn = _get_conn()
    with conn.cursor() as cur:
        if rebuild:
            cur.execute("""
                SELECT r.id, r.full_name, r.description, r.topics,
                       d.summary_ua, d.stack, d.use_cases, d.integration_notes,
                       d.key_dependencies
                FROM repositories r
                LEFT JOIN dossiers d ON d.repository_id = r.id
            """)
        else:
            # Тільки ті що ще не мають embedding
            cur.execute("""
                SELECT r.id, r.full_name, r.description, r.topics,
                       d.summary_ua, d.stack, d.use_cases, d.integration_notes,
                       d.key_dependencies
                FROM repositories r
                LEFT JOIN dossiers d ON d.repository_id = r.id
                LEFT JOIN embeddings e ON e.repository_id = r.id
                WHERE e.id IS NULL
            """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    conn.close()

    total = len(rows)
    if total == 0:
        logger.info("✨ Усі репо вже мають embeddings (--rebuild щоб перерахувати)")
        return

    logger.info(f"🚀 Будую embeddings для {total} репо...")
    success, failed = 0, 0

    for i, row in enumerate(rows, 1):
        repo = dict(zip(cols, row))
        text = build_repo_text(repo)
        if not text.strip():
            failed += 1
            continue

        vec = embed_text(text)
        if not vec:
            failed += 1
            logger.warning(f"[{i}/{total}] ❌ embed fail: {repo['full_name']}")
            continue

        if save_embedding(repo["id"], vec):
            success += 1
            if i % 25 == 0 or i == total:
                logger.info(f"[{i}/{total}] ✅ {repo['full_name']}")
        else:
            failed += 1

    logger.success(f"\n✅ Готово: {success} embeddings, {failed} помилок з {total}")
    logger.info("💡 Створіть IVFFlat індекс для швидкого пошуку:")
    logger.info("   psql -h localhost -U postgres -d dnk_git -c \"CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 16);\"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Перерахувати всі embeddings")
    args = parser.parse_args()
    run(rebuild=args.rebuild)
