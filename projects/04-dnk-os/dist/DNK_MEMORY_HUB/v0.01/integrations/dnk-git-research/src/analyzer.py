"""
analyzer.py — AI Analysis Module
Глибокий аналіз репозиторіїв через OmniRoute (Claude/Gemini) з fallback на пряме Gemini.
"""
from __future__ import annotations
import json
from loguru import logger


ANALYSIS_PROMPT = """Ти — технічний аналітик репозиторіїв. Ціль: Unified Repository Report для VibeCoder-підприємця.
Аналізуй РЕАЛЬНИЙ КОД та залежності. README може брехати — configs і entrypoints кажуть правду.

## Метадані:
**Назва**: {name} | **URL**: {url}
**Зірки**: {stars} | **Forks**: {forks} | **Мова**: {language} | **Ліцензія**: {license}
**Останній commit**: {pushed_at} ({days_since} днів тому)
**Теми**: {topics}
**Опис**: {description}

## Структура файлів:
{tree}

## README ({readme_quality}):
{readme}

## Залежності:
{dependencies}

## Конфігурація:
{configs}

## Документація:
{docs}

## Точки входу:
{entrypoints}

---

## Завдання:
Створи Unified Repository Report. Відповідай ТІЛЬКИ валідним JSON без пояснень.

{{
  "what_it_does": "Точний опис ЩО робить репо — 2-3 речення без маркетингу",
  "core_features": ["конкретна можливість 1", "можливість 2", "можливість 3"],
  "problems_it_solves": ["яку задачу вирішує 1", "задача 2"],
  "how_to_use": "Як підключити/інтегрувати — конкретні кроки або команди",

  "reverse_engineering": {{
    "key_files": ["РЕАЛЬНИЙ шлях з tree 1", "шлях 2"],
    "main_patterns": ["архітектурний патерн який можна взяти"],
    "can_be_extracted": "Що можна взяти окремо і як"
  }},

  "reading_order": [
    "README.md — загальне розуміння (~X токенів)",
    "main.py або index.ts — точки входу (~X токенів)",
    "src/core/ або lib/ — основна логіка (~X токенів)"
  ],

  "setup_signals": {{
    "has_dockerfile": true,
    "has_docker_compose": false,
    "has_env_example": true,
    "required_env_vars": ["VAR1", "VAR2"],
    "has_makefile": false,
    "direct_deps_count": 12,
    "readme_quality": "high | medium | low | absent"
  }},

  "integration_friction": {{
    "score": 7.5,
    "setup_complexity": "low | medium | high",
    "context_budget_tokens": 15000,
    "estimated_integration_hours": 4,
    "friction_factors": ["що ускладнює інтеграцію"],
    "friction_reducers": ["що спрощує інтеграцію"]
  }},

  "tech_stack": ["мова", "фреймворк", "ключова бібліотека"],
  "similar_to": ["схоже відоме рішення"],
  "best_used_for": ["сценарій використання 1", "сценарій 2"],
  "domain": "ai-agents | memory-systems | telegram-bots | saas-boilerplate | ecommerce | devtools | data-pipeline | analytics | other",
  "readiness": "production-ready | beta | prototype | experimental",
  "license_risk": "safe | warning | risky",
  "license_note": "MIT — безпечно для комерційного | GPL — ризик для SaaS"
}}

КРИТИЧНО:
- key_files та reading_order — ТІЛЬКИ реальні шляхи з tree вище
- integration_friction.score: 0-10 (вище = легше інтегрувати)
  Враховуй: +2 Docker, +2 .env.example, +1.5 tests, +1 CI, -1 за кожні 10 залежностей понад 5, -2 GPL
- context_budget_tokens: реалістична оцінка скільки токенів займе прочитання ключових файлів
- setup_signals.required_env_vars: тільки з .env.example або configs, не вигадуй
"""

SYNTHETIC_README_PROMPT = """Репозиторій не має README або він низької якості.
Твоя ціль — реконструювати призначення репо з коду.

## Репо: {name}
## Структура файлів:
{tree}

## Залежності:
{dependencies}

## Конфігурація:
{configs}

## Точки входу (перші 50 рядків):
{entrypoints}

---

Згенеруй Synthetic README. Відповідай ТІЛЬКИ JSON.

{{
  "synthetic_summary": "2-3 речення: що робить репо, на чому базується, для кого",
  "inferred_architecture": "опис архітектури з структури файлів",
  "inferred_stack": ["мова", "фреймворк"],
  "inferred_entry_command": "команда запуску якщо можна визначити",
  "confidence": "high | medium | low",
  "confidence_reason": "чому такий рівень впевненості"
}}
"""


def _assess_readme_quality(readme_text: str | None) -> str:
    if not readme_text or len(readme_text.strip()) < 50:
        return "absent"
    if len(readme_text) < 300:
        return "low"
    if len(readme_text) < 1500:
        return "medium"
    return "high"


def generate_synthetic_readme(repo: dict) -> dict:
    """Генерує Synthetic README коли README відсутній або низької якості."""
    from core.omni_router import router
    deep = repo.get("deep_context") or {}
    prompt = SYNTHETIC_README_PROMPT.format(
        name=repo.get("full_name", repo.get("name", "")),
        tree=repo.get("tree_text", "—")[:2000],
        dependencies=deep.get("dependencies", "—"),
        configs=deep.get("configs", "—"),
        entrypoints=deep.get("entrypoints", "—")[:1000],
    )
    try:
        result = router.complete_json(prompt)
        result["is_synthetic"] = True
        return result
    except Exception as e:
        logger.debug(f"Synthetic README error: {e}")
        return {"synthetic_summary": "", "is_synthetic": True, "confidence": "low"}


def analyze_repo(repo: dict) -> dict:
    """
    Глибокий аналіз одного репозиторію через OmniRoute (Claude/Gemini).
    Повертає Unified Repository Report з integration_friction, setup_signals, reading_order.
    """
    from core.omni_router import router

    deep = repo.get("deep_context") or {}
    readme_text = repo.get("readme_text") or ""
    readme_quality = _assess_readme_quality(readme_text)

    prompt = ANALYSIS_PROMPT.format(
        name=repo.get("full_name", repo.get("name", "")),
        url=repo.get("url", ""),
        stars=repo.get("stars", 0),
        forks=repo.get("forks", 0),
        language=repo.get("language", "Unknown"),
        license=repo.get("license", "Unknown"),
        pushed_at=repo.get("pushed_at", ""),
        days_since=repo.get("days_since_push", "?"),
        topics=", ".join(repo.get("topics", [])) or "—",
        description=repo.get("description", "—"),
        tree=repo.get("tree_text", "Дерево файлів недоступне"),
        readme_quality=readme_quality,
        readme=(readme_text or "README відсутній")[:4000],
        dependencies=deep.get("dependencies", "—"),
        configs=deep.get("configs", "—"),
        docs=deep.get("docs", "—"),
        entrypoints=deep.get("entrypoints", "—"),
    )

    logger.debug(f"🤖 Глибокий аналіз {repo.get('full_name', repo.get('name', '?'))}...")
    try:
        analysis = router.complete_json(prompt)

        # Synthetic README коли README відсутній або поганий
        if readme_quality in ("absent", "low") and not analysis.get("what_it_does"):
            logger.info(f"📝 Генерую Synthetic README для {repo.get('full_name', '?')} (readme: {readme_quality})")
            synthetic = generate_synthetic_readme(repo)
            analysis["synthetic_readme"] = synthetic
            if not analysis.get("what_it_does") and synthetic.get("synthetic_summary"):
                analysis["what_it_does"] = synthetic["synthetic_summary"]

        return analysis
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON parse error для {repo.get('name', '?')}: {e}")
        return _empty_analysis()
    except Exception as e:
        logger.error(f"❌ Analysis error для {repo.get('name', '?')}: {e}")
        return _empty_analysis()


TRIAGE_PROMPT = """Швидкий triage GitHub-репо. Тільки на основі метаданих.
Відповідай ТІЛЬКИ JSON.

Repo: {name} | ⭐{stars} | {language} | {license}
Опис: {description}
Теми: {topics}
Активність: {days_since} днів тому

{{
  "domain": "ai-agents | memory-systems | telegram-bots | saas-boilerplate | ecommerce | devtools | data-pipeline | analytics | other",
  "activity_level": "active | moderate | stale | abandoned",
  "worth_deep_dive": true/false,
  "skip_reason": "причина пропуску або null якщо worth_deep_dive=true"
}}
"""


def quick_triage(repo: dict) -> dict:
    """
    Швидкий аналіз без README/tree/файлів — лише метадані.
    ~5x швидше і дешевше за повний analyze_repo.
    """
    from core.omni_router import router
    prompt = TRIAGE_PROMPT.format(
        name=repo.get("full_name", "?"),
        stars=repo.get("stars", 0),
        language=repo.get("language", "?"),
        license=repo.get("license", "?"),
        description=(repo.get("description") or "—")[:300],
        topics=", ".join(repo.get("topics", [])) or "—",
        days_since=repo.get("days_since_push", "?"),
    )
    try:
        return router.complete_json(prompt)
    except Exception as e:
        logger.debug(f"Triage error: {e}")
        return {"domain": "other", "quick_score": 0, "worth_deep_dive": False}


def analyze_batch(repos: list[dict], with_readme: bool = False, with_tree: bool = True,
                  with_deep: bool = True, multi_pass: bool = False,
                  deep_dive_top: int = 5, deep_dive_threshold: float = 6.0) -> list[dict]:
    """
    Аналіз списку репозиторіїв.

    multi_pass=True — двофазний режим:
      1) Швидкий triage всіх (тільки метадані, дешево/швидко)
      2) Глибокий аналіз тільки top-N з quick_score >= threshold

    multi_pass=False — повний аналіз кожного (як раніше).
    """
    from .search import get_repo_details, get_repo_tree, get_repo_deep_context

    if multi_pass:
        logger.info(f"🔍 Phase 1: швидкий triage {len(repos)} репо...")
        triaged = []
        for i, repo in enumerate(repos, 1):
            t = quick_triage(repo)
            triaged.append({**repo, **t})
            if i % 10 == 0:
                logger.info(f"   triaged {i}/{len(repos)}")

        # Сортуємо за quick_score, беремо topN з worth_deep_dive
        candidates = [r for r in triaged if r.get("worth_deep_dive") and r.get("quick_score", 0) >= deep_dive_threshold]
        candidates.sort(key=lambda r: r.get("quick_score", 0), reverse=True)
        top = candidates[:deep_dive_top]
        skipped = [r for r in triaged if r not in top]

        logger.info(f"🔬 Phase 2: глибокий аналіз top-{len(top)} (з {len(triaged)} проаналізованих)")
        deep_results = []
        for i, repo in enumerate(top, 1):
            logger.info(f"[{i}/{len(top)}] Deep: {repo.get('full_name', '?')}")
            parts = (repo.get("full_name", "") or "").split("/")
            if len(parts) == 2:
                owner, name = parts[0], parts[1]
                if with_readme and not repo.get("readme_text"):
                    d = get_repo_details(owner, name)
                    if d:
                        repo.update(d)
                if with_tree and not repo.get("tree_text"):
                    repo["tree_text"] = get_repo_tree(owner, name)
                if with_deep and not repo.get("deep_context"):
                    repo["deep_context"] = get_repo_deep_context(owner, name, repo.get("tree_text", ""))
            analysis = analyze_repo(repo)
            deep_results.append({**repo, **analysis})

        # skipped лишаємо з триаж-полями (без deep dossier)
        return deep_results + [{**r, **_empty_analysis(),
                                "domain": r.get("domain", "other"),
                                "dnk_fit_score": r.get("quick_score", 0),
                                "summary_ua": r.get("description", "")[:200]}
                               for r in skipped]

    # === Single-pass mode (як раніше) ===
    results = []
    total = len(repos)
    for i, repo in enumerate(repos, 1):
        logger.info(f"[{i}/{total}] Analyzing: {repo.get('full_name', repo.get('name', '?'))}")
        parts = (repo.get("full_name", "") or "").split("/")
        if len(parts) == 2:
            owner, name = parts[0], parts[1]
            if with_readme and not repo.get("readme_text"):
                d = get_repo_details(owner, name)
                if d:
                    repo.update(d)
            if with_tree and not repo.get("tree_text"):
                repo["tree_text"] = get_repo_tree(owner, name)
            if with_deep and not repo.get("deep_context"):
                repo["deep_context"] = get_repo_deep_context(owner, name, repo.get("tree_text", ""))
        analysis = analyze_repo(repo)
        results.append({**repo, **analysis})
    return results


def _empty_analysis() -> dict:
    return {
        "what_it_does": "",
        "core_features": [],
        "problems_it_solves": [],
        "how_to_use": "",
        "reverse_engineering": {"key_files": [], "main_patterns": [], "can_be_extracted": ""},
        "reading_order": [],
        "setup_signals": {
            "has_dockerfile": False, "has_docker_compose": False,
            "has_env_example": False, "required_env_vars": [],
            "has_makefile": False, "direct_deps_count": 0, "readme_quality": "unknown",
        },
        "integration_friction": {
            "score": 0, "setup_complexity": "unknown", "context_budget_tokens": 0,
            "estimated_integration_hours": 0, "friction_factors": [], "friction_reducers": [],
        },
        "tech_stack": [],
        "similar_to": [],
        "best_used_for": [],
        "domain": "other",
        "readiness": "unknown",
        "license_risk": "unknown",
        "license_note": "",
    }


RECIPE_PROMPT = """Ти — архітектор інтеграції. Згенеруй Integration Recipe для VibeCoder.

## Репозиторій:
{repo_summary}

## Проєкт користувача:
{user_project}

---

Відповідай ТІЛЬКИ JSON.

{{
  "verdict": "✅ Рекомендовано | 🟡 Можна розглянути | ❌ Не рекомендую",
  "verdict_reason": "1-2 речення чому",
  "what_to_take": ["конкретний модуль/файл 1 — чому саме він"],
  "what_to_skip": ["що пропустити і чому"],
  "dependency_conflicts": ["конфлікт 1 або 'Конфліктів не виявлено'"],
  "env_setup": ["VAR1=... — пояснення", "VAR2=..."],
  "reading_order": [
    {{"file": "README.md", "why": "загальне розуміння", "tokens": 800}},
    {{"file": "main.py", "why": "точки входу", "tokens": 1200}}
  ],
  "claude_code_prompts": [
    "Prompt 1: Read [файл] and [файл]. Summarize: entry points, required env vars, main classes.",
    "Prompt 2: Extract [конкретний патерн/модуль]. Show how to use it with [user stack].",
    "Prompt 3: Generate minimal working example that integrates [what_to_take] into [user_project]."
  ],
  "warnings": ["попередження 1", "попередження 2"],
  "estimated_hours": 4
}}
"""


def generate_integration_recipe(repo: dict, user_project: str = "") -> dict:
    """
    Генерує Integration Recipe (Deliverable 3) для конкретного репо.
    Викликати тільки для 1-2 репо які користувач хоче інтегрувати.
    """
    from core.omni_router import router

    repo_summary = (
        f"Name: {repo.get('full_name', '?')}\n"
        f"What it does: {repo.get('what_it_does', '—')}\n"
        f"Tech stack: {', '.join(repo.get('tech_stack', []))}\n"
        f"Key files: {', '.join((repo.get('reverse_engineering') or {}).get('key_files', [])[:5])}\n"
        f"Can extract: {(repo.get('reverse_engineering') or {}).get('can_be_extracted', '—')}\n"
        f"Integration friction: {(repo.get('integration_friction') or {}).get('score', '?')}/10\n"
        f"License: {repo.get('license', '?')} ({repo.get('license_risk', '?')} risk)\n"
        f"Has Docker: {(repo.get('setup_signals') or {}).get('has_dockerfile', False)}\n"
        f"Required env vars: {', '.join((repo.get('setup_signals') or {}).get('required_env_vars', []))}"
    )

    prompt = RECIPE_PROMPT.format(
        repo_summary=repo_summary,
        user_project=user_project or "Не вказано — генеруй загальний рецепт",
    )

    try:
        recipe = router.complete_json(prompt)
        recipe["repo"] = repo.get("full_name", "?")
        recipe["generated_for"] = user_project
        return recipe
    except Exception as e:
        logger.error(f"❌ Recipe generation error: {e}")
        return {"error": str(e), "repo": repo.get("full_name", "?")}
