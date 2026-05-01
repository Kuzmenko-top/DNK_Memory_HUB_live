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

    _try_save_to_db(repos)
    save_to_qdrant(repos)

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


def _get_vertex_token() -> str | None:
    """OAuth2 токен для Vertex AI через service account."""
    sa_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(Path(__file__).parent.parent.parent.parent / "memory" / "ingestion" / "service-account.json"),
    )
    if not os.path.exists(sa_path):
        logger.debug(f"Service account not found: {sa_path}")
        return None
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        creds = service_account.Credentials.from_service_account_file(
            sa_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except Exception as e:
        logger.debug(f"Vertex auth error: {e}")
        return None


def _vertex_embed(text: str, token: str, project: str = "dnk-ai-agent") -> list[float] | None:
    """Генерує 768-dim вектор через Vertex AI text-embedding-004."""
    import json as _json
    import urllib.request, urllib.error
    url = (
        f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/us-central1/publishers/google/models/text-embedding-004:predict"
    )
    payload = _json.dumps({"instances": [{"task_type": "RETRIEVAL_DOCUMENT", "content": text[:8000]}]}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = _json.loads(r.read())
            return body["predictions"][0]["embeddings"]["values"]
    except Exception as e:
        logger.debug(f"Vertex embed error: {e}")
        return None


def _build_embed_text(repo: dict) -> str:
    """Текст для ембедингу: what_it_does + problems + best_used_for."""
    parts = [
        repo.get("what_it_does") or repo.get("description") or "",
        " ".join(repo.get("problems_it_solves") or []),
        " ".join(repo.get("best_used_for") or []),
        " ".join(repo.get("core_features") or []),
        repo.get("full_name", ""),
    ]
    return " ".join(p for p in parts if p).strip()


def save_to_qdrant(repos: list[dict]) -> bool:
    """Векторне збереження в Qdrant колекцію github_repos."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType
        import hashlib as _hashlib
    except ImportError:
        logger.warning("⚠️ qdrant-client not installed — skipping vector storage")
        return False

    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection = "github_repos"
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "dnk-ai-agent")

    try:
        client = QdrantClient(url=url, timeout=15)
    except Exception as e:
        logger.warning(f"⚠️ Qdrant not available: {e}")
        return False

    try:
        client.get_collection(collection)
    except Exception:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        logger.info(f"🗄️ Created Qdrant collection: {collection}")

    token = _get_vertex_token()
    if not token:
        logger.warning("⚠️ No Vertex AI token — skipping Qdrant embeddings")
        return False

    points = []
    for repo in repos:
        text = _build_embed_text(repo)
        if not text:
            continue
        vec = _vertex_embed(text, token, project=project)
        if not vec:
            continue
        key = repo.get("full_name") or repo.get("url") or str(repo.get("id", ""))
        point_id = _hashlib.md5(key.encode()).hexdigest()
        points.append(PointStruct(
            id=point_id,
            vector=vec,
            payload={
                "full_name": repo.get("full_name", ""),
                "url": repo.get("url", ""),
                "stars": repo.get("stars", 0),
                "what_it_does": repo.get("what_it_does", ""),
                "how_to_use": repo.get("how_to_use", ""),
                "problems_it_solves": repo.get("problems_it_solves", []),
                "best_used_for": repo.get("best_used_for", []),
                "core_features": repo.get("core_features", []),
                "tech_stack": repo.get("tech_stack", []),
                "integration_difficulty": repo.get("integration_difficulty", ""),
                "reverse_engineering": repo.get("reverse_engineering", {}),
                "domain": repo.get("domain", "other"),
                "readiness": repo.get("readiness", ""),
                "license": repo.get("license", ""),
            },
        ))

    if not points:
        logger.warning("⚠️ No embeddable repos (missing what_it_does text)")
        return False

    client.upsert(collection_name=collection, points=points)
    logger.success(f"✅ Qdrant: upserted {len(points)} repos → {collection}")
    return True


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
