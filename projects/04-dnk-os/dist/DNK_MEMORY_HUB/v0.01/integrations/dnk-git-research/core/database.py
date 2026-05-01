"""
database.py — PostgreSQL + pgvector storage
CRUD для repositories та dossiers. Активується коли є POSTGRES_URL у .env.
"""
from __future__ import annotations
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _get_conn():
    import psycopg2
    import psycopg2.extras
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise RuntimeError("POSTGRES_URL не задано в .env")
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


def is_available() -> bool:
    """Перевірити чи Postgres доступний."""
    try:
        conn = _get_conn()
        conn.close()
        return True
    except Exception:
        return False


def _to_str_list(value) -> list[str]:
    """Привести значення до list[str]. Захист від AI що повертає string замість list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    if isinstance(value, str):
        # Якщо AI повернув рядок — обгортаємо у список, або повертаємо пустий якщо це placeholder
        clean = value.strip()
        if not clean or clean.lower().startswith(("n/a", "none", "—", "-")):
            return []
        return [clean[:500]]
    return []


def save_repo(repo: dict) -> Optional[int]:
    """
    Upsert репозиторій + dossier у Postgres.
    Повертає repository_id або None при помилці.
    """
    full_name = repo.get("full_name") or repo.get("name")
    if not full_name:
        return None

    # Збагачуємо похідними сигналами перед збереженням
    try:
        from core.signals import enrich_with_signals
        repo = enrich_with_signals(repo)
    except Exception as e:
        logger.debug(f"Signal enrichment skip: {e}")

    try:
        import psycopg2.extras
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO repositories
                        (full_name, name, url, owner_type, description, stars, forks, watchers,
                         language, languages_breakdown, license, topics,
                         pushed_at, days_since_push,
                         latest_release_tag, latest_release_date, release_cadence_days,
                         contributors_count, has_tests, has_ci, has_changelog,
                         readme_text, tree_text,
                         newness_score, maintenance_status, popularity_tier, license_permissions,
                         updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                    ON CONFLICT (full_name) DO UPDATE SET
                        stars               = EXCLUDED.stars,
                        forks               = EXCLUDED.forks,
                        watchers            = EXCLUDED.watchers,
                        description         = EXCLUDED.description,
                        languages_breakdown = EXCLUDED.languages_breakdown,
                        days_since_push     = EXCLUDED.days_since_push,
                        latest_release_tag  = EXCLUDED.latest_release_tag,
                        latest_release_date = EXCLUDED.latest_release_date,
                        release_cadence_days = EXCLUDED.release_cadence_days,
                        contributors_count  = EXCLUDED.contributors_count,
                        has_tests           = EXCLUDED.has_tests,
                        has_ci              = EXCLUDED.has_ci,
                        has_changelog       = EXCLUDED.has_changelog,
                        readme_text         = EXCLUDED.readme_text,
                        tree_text           = EXCLUDED.tree_text,
                        newness_score       = EXCLUDED.newness_score,
                        maintenance_status  = EXCLUDED.maintenance_status,
                        popularity_tier     = EXCLUDED.popularity_tier,
                        license_permissions = EXCLUDED.license_permissions,
                        updated_at          = NOW()
                    RETURNING id
                """, (
                    full_name,
                    repo.get("name") or full_name.split("/")[-1],
                    repo.get("url") or f"https://github.com/{full_name}",
                    repo.get("owner_type"),
                    repo.get("description"),
                    int(repo.get("stars") or 0),
                    int(repo.get("forks") or 0),
                    int(repo.get("watchers") or 0),
                    repo.get("language"),
                    json.dumps(repo.get("languages_breakdown") or {}),
                    repo.get("license"),
                    _to_str_list(repo.get("topics")),
                    repo.get("pushed_at"),
                    repo.get("days_since_push"),
                    repo.get("latest_release_tag"),
                    repo.get("latest_release_date"),
                    repo.get("release_cadence_days"),
                    repo.get("contributors_count"),
                    bool(repo.get("has_tests", False)),
                    bool(repo.get("has_ci", False)),
                    bool(repo.get("has_changelog", False)),
                    (repo.get("readme_text") or "")[:50000],
                    (repo.get("tree_text") or "")[:20000],
                    repo.get("newness_score"),
                    repo.get("maintenance_status"),
                    repo.get("popularity_tier"),
                    json.dumps(repo.get("license_permissions") or {}),
                ))
                repo_id = cur.fetchone()[0]

                # Upsert dossier (delete + insert — простіше ніж ON CONFLICT по FK)
                if repo.get("dnk_total_score") is not None or repo.get("dnk_fit_score"):
                    cur.execute("DELETE FROM dossiers WHERE repository_id = %s", (repo_id,))
                    cur.execute("""
                        INSERT INTO dossiers
                            (repository_id, stack, readiness, dnk_fit_score, dnk_fit_reason,
                             use_cases, integration_complexity, integration_notes, domain,
                             target_audience, recommendation, summary_ua, dnk_total_score,
                             capabilities, integrations, limitations, key_modules,
                             key_dependencies, deployment_hints, model_used)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        repo_id,
                        repo.get("stack"),
                        repo.get("readiness"),
                        float(repo.get("dnk_fit_score") or 0),
                        repo.get("dnk_fit_reason"),
                        _to_str_list(repo.get("use_cases")),
                        repo.get("integration_complexity"),
                        repo.get("integration_notes"),
                        repo.get("domain", "other"),
                        repo.get("target_audience"),
                        repo.get("recommendation"),
                        repo.get("summary_ua"),
                        float(repo.get("dnk_total_score") or 0),
                        _to_str_list(repo.get("capabilities")),
                        _to_str_list(repo.get("integrations")),
                        _to_str_list(repo.get("limitations")),
                        json.dumps(repo.get("key_modules") or []),
                        _to_str_list(repo.get("key_dependencies")),
                        repo.get("deployment_hints"),
                        repo.get("model_used", "gemini-2.5-flash"),
                    ))

        conn.close()
        return repo_id
    except Exception as e:
        logger.error(f"❌ DB save error для {full_name}: {e}")
        return None


def get_repo_by_name(full_name: str) -> Optional[dict]:
    """Отримати репо + dossier по full_name."""
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*, d.stack, d.readiness, d.dnk_fit_score, d.dnk_fit_reason,
                       d.use_cases, d.integration_complexity, d.integration_notes,
                       d.domain, d.recommendation, d.summary_ua, d.dnk_total_score
                FROM repositories r
                LEFT JOIN dossiers d ON d.repository_id = r.id
                WHERE r.full_name = %s
                LIMIT 1
            """, (full_name,))
            row = cur.fetchone()
            if row:
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        conn.close()
    except Exception as e:
        logger.error(f"❌ DB get error: {e}")
    return None


def search_repos(
    query: str = "",
    domain: str | None = None,
    min_score: float = 0,
    limit: int = 20,
) -> list[dict]:
    """Пошук репозиторіїв з фільтрами."""
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            conditions = ["d.dnk_total_score >= %s"]
            params: list = [min_score]

            if domain:
                conditions.append("d.domain = %s")
                params.append(domain)

            if query:
                conditions.append("""
                    (r.full_name ILIKE %s
                     OR r.description ILIKE %s
                     OR d.summary_ua ILIKE %s
                     OR %s = ANY(r.topics))
                """)
                q = f"%{query}%"
                params += [q, q, q, query.lower()]

            where = " AND ".join(conditions)
            params.append(limit)

            cur.execute(f"""
                SELECT r.full_name, r.name, r.url, r.description, r.stars, r.language,
                       r.topics, d.domain, d.recommendation, d.summary_ua,
                       d.dnk_total_score, d.dnk_fit_score, d.stack, d.readiness
                FROM repositories r
                LEFT JOIN dossiers d ON d.repository_id = r.id
                WHERE {where}
                ORDER BY d.dnk_total_score DESC NULLS LAST
                LIMIT %s
            """, params)

            cols = [desc[0] for desc in cur.description]
            results = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ DB search error: {e}")
        return []


def get_stats() -> dict:
    """Статистика бази даних."""
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM repositories")
            total = cur.fetchone()[0]
            cur.execute("""
                SELECT domain, COUNT(*) FROM dossiers
                GROUP BY domain ORDER BY COUNT(*) DESC
            """)
            domains = dict(cur.fetchall())
            cur.execute("""
                SELECT r.full_name, d.dnk_total_score FROM repositories r
                JOIN dossiers d ON d.repository_id = r.id
                ORDER BY d.dnk_total_score DESC LIMIT 5
            """)
            top5 = [{"name": row[0], "score": row[1]} for row in cur.fetchall()]
        conn.close()
        return {"total": total, "domains": domains, "top5": top5}
    except Exception as e:
        logger.error(f"❌ DB stats error: {e}")
        return {"total": 0, "domains": {}, "top5": []}
