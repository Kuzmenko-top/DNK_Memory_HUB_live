"""
analyzer.py — AI Analysis Module
Глибокий аналіз репозиторіїв через OmniRoute (Claude/Gemini) з fallback на пряме Gemini.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from loguru import logger

# Додаємо корінь проекту до sys.path для доступу до core
root = Path(__file__).parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))


ANALYSIS_PROMPT = """Ти — технічний аналітик для VibeCoding-підприємців.
Проаналізуй GitHub-репозиторій ГЛИБОКО, на основі реального коду та залежностей.
Твоя ціль — виділити **ПЕРЕВИКОРИСТОВУВАНІ МОДУЛІ** для подальшої декомпозиції задач.

## Метадані:
**Назва**: {name} | **URL**: {url}
**Зірки**: {stars} | **Forks**: {forks} | **Мова**: {language} | **Ліцензія**: {license}
**Останній commit**: {pushed_at} ({days_since} днів тому)
**Теми**: {topics}
**Опис**: {description}

## Структура файлів:
{tree}

## README:
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
Проаналізуй ВЕСЬ контекст. Залежності та entrypoints важливіші за README.
Відповідай ТІЛЬКИ валідним JSON.

{{
  "stack": "Точний стек з конкретними бібліотеками",
  "readiness": "production-ready | beta | prototype | experimental",
  "dnk_fit_score": <число 1-10>,
  "dnk_fit_reason": "Чому підходить (1-2 речення)",
  "domain": "ai-agents | memory-systems | telegram-bots | saas-boilerplate | ecommerce | devtools | logistics | analytics | other",
  "target_audience": "Хто цільова аудиторія (developers/businesses/researchers/etc)",
  "recommendation": "✅ Рекомендовано | 🟡 Можна розглянути | ❌ Не підходить",
  "summary_ua": "Що робить, на чому базується, для кого (3-4 речення українською)",

  "capabilities": ["конкретна функція 1", "функція 2", "функція 3"],
  "use_cases": ["конкретний use case 1", "use case 2", "use case 3"],
  "integrations": ["з чим стикується (Postgres, Redis, Stripe, Telegram API тощо)"],
  "limitations": ["обмеження 1 (наприклад: підтримує тільки English)", "обмеження 2"],

  "key_modules": [
    {{
      "name": "auth_jwt",
      "path": "src/auth/",
      "files": ["src/auth/jwt.py", "src/auth/middleware.py"],
      "purpose": "JWT signing та middleware верифікації",
      "reusable": true,
      "dependencies": ["pyjwt"]
    }}
  ],

  "key_dependencies": ["топ-5 залежностей"],
  "integration_complexity": "low | medium | high",
  "integration_notes": "Що треба щоб інтегрувати: env vars, кроки",
  "deployment_hints": "Docker/cloud/local — на основі configs"
}}

КРИТИЧНО про key_modules:
- Це ОКРЕМІ модулі/підсистеми, які можна взяти ОКРЕМО від решти репо
- Якщо репо моноліт без чіткої модуляризації — поверни 1-2 модулі (cores/main)
- Якщо репо це monorepo з очевидними бібліотеками — окремий module per кожна бібліотека
- files мають бути РЕАЛЬНИМИ шляхами з tree вище (не вигадуй)
- reusable: true тільки якщо модуль самодостатній і має чіткий interface
- 2-5 модулів оптимально, не більше 7

DNK Fit Score:
- 9-10: Ідеально, готовий до інтеграції (MIT/Apache, активний)
- 7-8: Добре, мінімальні зміни
- 5-6: Частково, потрібна адаптація
- 1-4: Слабо/не підходить (abandoned, GPL для closed-source SaaS)
"""


def analyze_repo(repo: dict) -> dict:
    """
    Глибокий аналіз одного репозиторію через OmniRoute (Claude/Gemini).
    Повертає збагачений dict з AI-метриками.
    """
    from core.omni_router import router

    deep = repo.get("deep_context") or {}
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
        readme=(repo.get("readme_text") or "README недоступний")[:4000],
        dependencies=deep.get("dependencies", "—"),
        configs=deep.get("configs", "—"),
        docs=deep.get("docs", "—"),
        entrypoints=deep.get("entrypoints", "—"),
    )

    logger.debug(f"🤖 Глибокий аналіз {repo.get('full_name', repo.get('name', '?'))}...")
    try:
        analysis = router.complete_json(prompt)
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
  "domain": "ai-agents | memory-systems | telegram-bots | saas-boilerplate | ecommerce | devtools | logistics | analytics | other",
  "quick_score": <число 1-10 на основі тільки метаданих>,
  "worth_deep_dive": true/false
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
        "stack": "Невідомо",
        "readiness": "unknown",
        "dnk_fit_score": 0,
        "dnk_fit_reason": "Аналіз не вдався",
        "domain": "other",
        "target_audience": "",
        "recommendation": "❓ Без оцінки",
        "summary_ua": "",
        "capabilities": [],
        "use_cases": [],
        "integrations": [],
        "limitations": [],
        "key_modules": [],
        "key_dependencies": [],
        "integration_complexity": "unknown",
        "integration_notes": "",
        "deployment_hints": "",
    }
