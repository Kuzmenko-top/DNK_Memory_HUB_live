"""
storage.py — Knowledge Base Storage
Збереження репо в JSON-бібліотеку та Qdrant для семантичного пошуку
"""
from __future__ import annotations
import os
import json
from datetime import datetime
from pathlib import Path
from loguru import logger


def _library_path() -> Path:
    base = Path(__file__).parent.parent / "data" / "library.json"
    base.parent.mkdir(parents=True, exist_ok=True)
    return base


def load_library() -> dict:
    """Завантажити локальну JSON-бібліотеку репозиторіїв."""
    path = _library_path()
    if not path.exists():
        return {"repos": {}, "meta": {"total": 0, "last_updated": ""}}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_to_library(repos: list[dict]) -> int:
    """
    Зберегти репозиторії в JSON-бібліотеку.
    Повертає кількість нових доданих репо.
    """
    library = load_library()
    stored = library.get("repos", {})
    added = 0

    for repo in repos:
        key = repo.get("full_name") or repo.get("url") or str(repo.get("id", ""))
        if not key:
            continue
        is_new = key not in stored
        stored[key] = {
            **repo,
            "saved_at": datetime.utcnow().isoformat(),
        }
        if is_new:
            added += 1

    library["repos"] = stored
    library["meta"] = {
        "total": len(stored),
        "last_updated": datetime.utcnow().isoformat(),
    }

    path = _library_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(library, f, ensure_ascii=False, indent=2)

    logger.success(f"✅ Library updated: {added} new repos (total: {len(stored)})")

    # Persist до PostgreSQL якщо доступно
    _try_save_to_db(repos)

    return added


def _try_save_to_db(repos: list[dict]) -> None:
    try:
        from core.database import save_repo, is_available
        if not is_available():
            return
        saved_ids = []
        for r in repos:
            rid = save_repo(r)
            if rid is not None:
                saved_ids.append((rid, r))
        if saved_ids:
            logger.debug(f"💾 DB: збережено {len(saved_ids)}/{len(repos)} репо")
        # Auto-embed нові репо (якщо є AI dossier)
        _try_embed(saved_ids)
    except Exception as e:
        logger.debug(f"DB skip: {e}")


def _try_embed(saved: list[tuple[int, dict]]) -> None:
    """Авто-генерація ембедингів для свіжо збережених репо з AI dossier."""
    try:
        from core.embeddings import embed_text, build_repo_text, save_embedding
        embedded = 0
        for repo_id, repo in saved:
            # Embed тільки якщо є AI-аналіз (інакше текст бідний)
            if not (repo.get("summary_ua") or repo.get("dnk_fit_score")):
                continue
            text = build_repo_text(repo)
            if not text.strip():
                continue
            vec = embed_text(text)
            if vec and save_embedding(repo_id, vec):
                embedded += 1
        if embedded:
            logger.debug(f"🧬 Embeddings: створено {embedded}/{len(saved)}")
    except Exception as e:
        logger.debug(f"Embed skip: {e}")


def search_library(query: str, domain: str | None = None, min_score: float = 0) -> list[dict]:
    """Пошук в локальній бібліотеці по ключових словах та фільтрах."""
    library = load_library()
    results = []
    query_lower = query.lower()

    for key, repo in library.get("repos", {}).items():
        # Domain filter
        if domain and repo.get("domain", "") != domain:
            continue
        # Score filter
        if repo.get("dnk_total_score", 0) < min_score:
            continue
        # Text search
        searchable = " ".join([
            repo.get("name", ""),
            repo.get("description", ""),
            repo.get("summary_ua", ""),
            " ".join(repo.get("topics", [])),
            " ".join(repo.get("use_cases", [])),
        ]).lower()

        if query_lower in searchable:
            results.append(repo)

    results.sort(key=lambda r: r.get("dnk_total_score", 0), reverse=True)
    return results


def save_to_qdrant(repos: list[dict]) -> bool:
    """Векторне збереження в Qdrant (Phase 2)."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance

        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        collection = os.getenv("QDRANT_COLLECTION", "github-research")
        client = QdrantClient(url=url, timeout=10)

        # Ensure collection exists (768 dims for text-embedding-3-small-like)
        try:
            client.get_collection(collection)
        except Exception:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )

        # TODO: Add real embeddings in Phase 2 (Ollama nomic-embed-text)
        logger.info(f"💾 Qdrant integration ready (Phase 2). {len(repos)} repos queued.")
        return True
    except ImportError:
        logger.warning("⚠️ qdrant-client not installed — skipping vector storage")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Qdrant not available: {e}")
        return False


def get_library_stats() -> dict:
    """Статистика бібліотеки."""
    library = load_library()
    repos = list(library.get("repos", {}).values())
    domains: dict[str, int] = {}
    for r in repos:
        d = r.get("domain", "other")
        domains[d] = domains.get(d, 0) + 1

    top5 = sorted(repos, key=lambda r: r.get("dnk_total_score", 0), reverse=True)[:5]
    return {
        "total": len(repos),
        "domains": domains,
        "top5": [{"name": r.get("full_name", "?"), "score": r.get("dnk_total_score", 0)} for r in top5],
        "last_updated": library.get("meta", {}).get("last_updated", "—"),
    }
