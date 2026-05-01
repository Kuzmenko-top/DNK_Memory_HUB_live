"""
mcp_server/server.py — DNK Git Research MCP Server
Інструменти для AI-агентів: пошук репозиторіїв, отримання dossier.

Запуск: python mcp_server/server.py
Або через Claude Code: mcp add dnk-git-research python mcp_server/server.py
"""
from __future__ import annotations
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from loguru import logger

mcp = FastMCP("DNK_Git_Research")


@mcp.tool()
def get_repo_dossier(full_name: str) -> str:
    """
    Отримати повний dossier репозиторію.
    full_name: owner/repo (наприклад: 'langchain-ai/langchain')
    """
    # Спочатку DB, потім JSON-бібліотека
    try:
        from core.database import get_repo_by_name, is_available
        if is_available():
            repo = get_repo_by_name(full_name)
            if repo:
                return json.dumps(repo, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        logger.warning(f"DB fallback to JSON: {e}")

    from src.storage import load_library
    lib = load_library()
    repo = lib.get("repos", {}).get(full_name)
    if not repo:
        return f"Репозиторій '{full_name}' не знайдено в бібліотеці."
    return json.dumps(repo, ensure_ascii=False, default=str, indent=2)


@mcp.tool()
def semantic_search_repos(query: str, limit: int = 10, min_score: float = 0) -> str:
    """
    Семантичний пошук репозиторіїв через pgvector embeddings.
    Знаходить репо за СМИСЛОМ запиту, не за ключовими словами.
    query: природний опис ('векторна пам'ять для агентів', 'fast api з PostgreSQL')
    min_score: фільтр по DNK Score (0-10), 0 = без фільтру
    """
    try:
        from core.embeddings import semantic_search
        results = semantic_search(query, limit=limit, min_score=min_score)
        if not results:
            return f"Не знайдено результатів. Можливо embeddings ще не побудовані — запусти `python scripts/build_embeddings.py`"
        return json.dumps(results, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        return f"Помилка семантичного пошуку: {e}"


@mcp.tool()
def search_repos_by_task(task: str, min_score: float = 7.0, limit: int = 10) -> str:
    """
    Знайти репозиторії підходящі для конкретної задачі.
    task: опис задачі або технологія ('telegram bot', 'rag pipeline', 'shopify app')
    min_score: мінімальний DNK Score (0-10), за замовчуванням 7.0
    """
    try:
        from core.database import search_repos, is_available
        if is_available():
            results = search_repos(query=task, min_score=min_score, limit=limit)
            if results:
                return json.dumps(results, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        logger.warning(f"DB fallback to JSON: {e}")

    from src.storage import search_library
    results = search_library(task, min_score=min_score)[:limit]
    if not results:
        return f"Не знайдено репозиторіїв для задачі: '{task}'"
    return json.dumps(results, ensure_ascii=False, default=str, indent=2)


@mcp.tool()
def get_top_repos(domain: str | None = None, limit: int = 10) -> str:
    """
    Отримати топ репозиторіїв за DNK Score.
    domain: фільтр по домену (ai-agents, memory-systems, telegram-bots,
            saas-boilerplate, ecommerce, devtools, logistics, analytics)
    limit: кількість результатів (макс 50)
    """
    limit = min(limit, 50)
    try:
        from core.database import search_repos, is_available
        if is_available():
            results = search_repos(domain=domain, limit=limit)
            return json.dumps(results, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        logger.warning(f"DB fallback to JSON: {e}")

    from src.storage import load_library
    lib = load_library()
    repos = list(lib.get("repos", {}).values())
    if domain:
        repos = [r for r in repos if r.get("domain") == domain]
    repos.sort(key=lambda r: r.get("dnk_total_score", 0), reverse=True)
    return json.dumps(repos[:limit], ensure_ascii=False, default=str, indent=2)


@mcp.tool()
def decompose_task(task: str, top: int = 10, min_score: float = 5.0) -> str:
    """
    Розкласти задачу на підзадачі та підібрати open-source репо/модулі для кожної.
    Повертає план з: subtasks (вибраний repo + reused_parts + rationale),
    integration_plan, gaps, risks, license_check.

    task: опис задачі ('побудувати telegram-бота з RAG-пам'яттю на українській')
    top: к-сть кандидатів з бібліотеки (default 10)
    min_score: мін DNK Score кандидатів (default 5.0)
    """
    try:
        from core.decompose import decompose_task as _decompose
        plan = _decompose(task, top_n=top, min_score=min_score)
        return json.dumps(plan, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        return f"Помилка декомпозиції: {e}"


@mcp.tool()
def check_license_compatibility(licenses: list[str]) -> str:
    """
    Перевірити сумісність набору SPDX-ліцензій (приклад: ['MIT', 'GPL-3.0', 'Apache-2.0']).
    Повертає warnings + blockers + чи безпечно для комерційного SaaS.
    """
    try:
        from core.licenses import check_compatibility, safe_for_commercial_saas
        compat = check_compatibility(licenses)
        saas_safe, saas_reasons = safe_for_commercial_saas(licenses)
        return json.dumps({
            "licenses": licenses,
            "compatible": compat["compatible"],
            "warnings": compat["warnings"],
            "blockers": compat["blockers"],
            "safe_for_commercial_saas": saas_safe,
            "saas_concerns": saas_reasons,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Помилка перевірки ліцензій: {e}"


@mcp.tool()
def get_library_stats() -> str:
    """Статистика бібліотеки: кількість репозиторіїв, домени, топ-5."""
    try:
        from core.database import get_stats, is_available
        if is_available():
            stats = get_stats()
            stats["source"] = "postgresql"
            return json.dumps(stats, ensure_ascii=False, indent=2)
    except Exception:
        pass

    from src.storage import get_library_stats
    stats = get_library_stats()
    stats["source"] = "json"
    return json.dumps(stats, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
