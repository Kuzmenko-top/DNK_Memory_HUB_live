"""
expert_analyst.py — Expert OSS Analyst Skill
Цей модуль реалізує глибокий прагматичний аудит репозиторіїв за 15-пунктовою структурою.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime, timezone

# Додаємо корінь проекту до sys.path для доступу до core
root = Path(__file__).parent.parent.parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

EXPERT_ANALYST_PROMPT = """Ти — senior OSS analyst, solution architect та integration reviewer.
Твоє завдання: проаналізувати GitHub-репозиторій не як “цікавий проект”, а як кандидата для:
1) прямої інтеграції, 2) часткового перевикористання модулів, 3) запозичення архітектурних патернів, 4) відхилення.

Працюй прагматично. Не переоцінюй README. Якщо даних недостатньо — прямо вкажи невизначеність.
Не хвали репозиторій без доказів. Шукай не тільки плюси, а й friction, hidden complexity, abandonment risk, lock-in, demo-ware signals.

## Вхідні дані репозиторію:
Назва: {name}
URL: {url}
Метадані: Stars: {stars}, Forks: {forks}, Language: {language}, License: {license}
Останній commit: {pushed_at}
Опис: {description}

## Структура файлів:
{tree}

## Глибокий контекст (залежності, точки входу, конфіги):
{deep_context}

## README:
{readme}

---

Ціль аналізу:
- визначити, чи варто брати цей репозиторій у нашу систему;
- якщо так, то як саме: fork / dependency / copy modules / extract patterns / use only ideas;
- оцінити, чи це готовий building block, чи лише reference implementation;
- оцінити fit для AI-agent, RAG, memory, automation, Shopify, research або internal tooling use cases.

Поверни відповідь СТРОГО у форматі Markdown згідно з наступною структурою:

# 1. Executive Summary
(2–4 речення: що це за репозиторій, для чого він реально придатний, і головний вердикт)
Фінальний статус: STRONG FIT | CONDITIONAL FIT | PATTERN ONLY | NOT RECOMMENDED

# 2. Repository Snapshot
(repo name, owner, URL, stats, language, license, freshness, maturity: demo/prototype/MVP/reusable OSS/production-leaning)

# 3. What It Actually Does
(яку проблему вирішує, workflow, core value, що НЕ входить у scope)

# 4. Architecture Type
(класифікація: library/app/tool/framework/starter/infra/CLI/plugin/prototype)
(runtime components, storage, dependencies, API surface, config style, deployment model)

# 5. Integration Potential
(Оцінка 1-10 для adoption, reuse, API wrapping, patterns, UI, infra)

# 6. Integration Friction
(Оцінка 1-10 для setup, dependency, infra, environment, code complexity, maintenance, lock-in)
Total Integration Friction: X/10

# 7. Code Reuse Targets
(конкретні файли/папки для перевикористання: path, value high/medium/low, mode adapt/copy/reference, risk)

# 8. Reading Order for an AI Coding Agent
(start files, architecture, execution path, config, token budget, fastest path)

# 9. Production Readiness
(deployability, observability, test coverage, security, scaling)
Статус: Production-ready | Production-with-work | Prototype-only

# 10. Risk Analysis
(maintenance, abandonment, security, legal, architecture, hidden complexity - low/medium/high)

# 11. Strategic Fit
(AI agents, RAG, memory, automation, Shopify, research, knowledge systems)
Таблиця: Use case | Fit score 1–10 | Why | Recommended use mode

# 12. Best Extraction Strategy
(Adopt as-is / Fork / Extract modules / Wrap as service / Pattern only / Reject)
(чому, що брати першим, що не чіпати)

# 13. Integration Recipe
(практичний план: 1. clone/read, 2. deps, 3. isolate, 4. rewrite, 5. test, 6. validate)

# 14. Final Verdict
Verdict:
Best use:
Worst use:
Time-to-first-value:
Hidden trap:
Recommended next action:

# 15. DNK-Style Post Analysis
- ReBurn fit: 1–10
- Shopify fit: 1–10
- DNK_Git_Research fit: 1–10
- Agent-memory-stack fit: 1–10
- Can this repo become: (feature/standalone tool/module/inspiration?)
- Best project match in our ecosystem
- Expected implementation effort: XS / S / M / L / XL
- Suggested owner role: (researcher/architect/backend/frontend/ops agent)

КРИТИЧНО:
- пиши коротко, конкретно, технічно;
- без маркетингових фраз;
- з фокусом на reuse, fit, friction та risk.
- Confidence: low / medium / high.
"""

def analyze_repo_expert(repo: dict) -> str:
    """
    Виконує глибокий експертний аналіз репозиторію.
    Повертає Markdown-текст звіту.
    """
    from core.omni_router import router
    
    deep = repo.get("deep_context") or {}
    deep_str = f"Dependencies: {deep.get('dependencies', '—')}\nEntrypoints: {deep.get('entrypoints', '—')}\nConfigs: {deep.get('configs', '—')}"
    
    prompt = EXPERT_ANALYST_PROMPT.format(
        name=repo.get("full_name", repo.get("name", "")),
        url=repo.get("url", ""),
        stars=repo.get("stars", 0),
        forks=repo.get("forks", 0),
        language=repo.get("language", "Unknown"),
        license=repo.get("license", "Unknown"),
        pushed_at=repo.get("pushed_at", ""),
        description=repo.get("description", "—"),
        tree=repo.get("tree_text", "Дерево файлів недоступне")[:3000],
        deep_context=deep_str[:2000],
        readme=(repo.get("readme_text") or "README відсутній")[:5000]
    )
    
    logger.info(f"🧐 Запуск експертного аудиту для {repo.get('full_name', '?')}...")
    try:
        # Використовуємо Claude 3.5 Sonnet або Gemini 1.5 Pro для кращого архітектурного аналізу
        # OmniRouter за замовчуванням вибере найкращу модель
        report = router.complete(prompt)
        return report
    except Exception as e:
        logger.error(f"❌ Expert analysis error: {e}")
        return f"# Error in Expert Analysis\n{str(e)}"

def save_expert_report(repo_name: str, content: str) -> str:
    """Зберігає експертний звіт у папку data/reports/"""
    from pathlib import Path
    slug = repo_name.replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = Path(__file__).parent.parent / "data" / "reports" / f"expert_{slug}_{ts}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)
