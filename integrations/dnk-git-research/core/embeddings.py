"""
embeddings.py — Векторні embeddings для семантичного пошуку
Використовує Gemini text-embedding-004 (768 dims, безкоштовний для дослідницьких цілей).
Зберігає у pgvector таблицю embeddings.
"""
from __future__ import annotations
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

EMBED_MODEL = os.getenv("EMBED_MODEL", "models/gemini-embedding-001")
EMBED_DIMS = 768  # збігається з vector(768) у схемі


def embed_text(text: str) -> list[float] | None:
    """
    Згенерувати 768-dim ембединг через Gemini.
    Повертає вектор або None при помилці.
    """
    if not text or len(text.strip()) < 5:
        return None
    try:
        from google import genai
        from google.genai import types
        
        # SDK автоматично підтягує GOOGLE_API_KEY з env
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
        truncated = text[:8000]
        
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=truncated,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBED_DIMS,
            )
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error(f"❌ Embedding error: {e}")
        return None


def build_repo_text(repo: dict) -> str:
    """
    Сформувати текст для embedding з даних репо.
    Включає: ім'я + опис + summary_ua + use_cases + stack + topics.
    """
    parts = [
        repo.get("full_name", ""),
        repo.get("description", "") or "",
        repo.get("summary_ua", "") or "",
        repo.get("stack", "") or "",
        repo.get("integration_notes", "") or "",
    ]
    use_cases = repo.get("use_cases", [])
    if use_cases:
        parts.append("Use cases: " + "; ".join(use_cases))
    topics = repo.get("topics", [])
    if topics:
        parts.append("Topics: " + ", ".join(topics))
    deps = repo.get("key_dependencies", [])
    if deps:
        parts.append("Key deps: " + ", ".join(deps))
    return "\n".join(p for p in parts if p)


def save_embedding(repository_id: int, embedding: list[float]) -> bool:
    """Зберегти ембединг у pgvector таблицю."""
    from core.database import _get_conn
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                # Upsert: видаляємо старий + вставляємо новий
                cur.execute("DELETE FROM embeddings WHERE repository_id = %s", (repository_id,))
                cur.execute(
                    "INSERT INTO embeddings (repository_id, embedding) VALUES (%s, %s)",
                    (repository_id, str(embedding)),
                )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Save embedding error для repo_id={repository_id}: {e}")
        return False


def semantic_search(query: str, limit: int = 10, min_score: float = 0) -> list[dict]:
    """
    Семантичний пошук через cosine similarity у pgvector.
    Повертає репозиторії відсортовані за схожістю до query.
    """
    query_vec = embed_text(query)
    if not query_vec:
        return []

    from core.database import _get_conn
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT r.full_name, r.description, r.stars, r.url,
                       d.domain, d.summary_ua, d.dnk_total_score, d.recommendation,
                       1 - (e.embedding <=> %s::vector) AS similarity
                FROM embeddings e
                JOIN repositories r ON r.id = e.repository_id
                LEFT JOIN dossiers d ON d.repository_id = r.id
                WHERE COALESCE(d.dnk_total_score, 0) >= %s
                ORDER BY e.embedding <=> %s::vector
                LIMIT %s
            """, (str(query_vec), min_score, str(query_vec), limit))
            cols = [desc[0] for desc in cur.description]
            results = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ Semantic search error: {e}")
        return []
