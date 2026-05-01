"""
decompose.py — Декомпозиція задачі на open-source компоненти
Бере опис задачі → розбиває на підзадачі → шукає підходящі репо/модулі → будує план інтеграції.
"""
from __future__ import annotations
import json
from loguru import logger


DECOMPOSE_PROMPT = """Ти — архітектор open-source рішень для VibeCoding-підприємців.
Користувач має задачу. Твоя робота — розкласти її на підзадачі та підібрати для кожної
підзадачі open-source репозиторій (або модуль з нього), використовуючи бібліотеку нижче.

## ЗАДАЧА:
{task}

## БІБЛІОТЕКА (топ-{n} семантично близьких репозиторіїв):
{candidates}

---

## Завдання:
Розклади задачу на 2-5 підзадач. Для кожної — обери репо з бібліотеки (якщо є підходяще)
АБО познач як gap (немає рішення). Якщо репо містить багато модулів — обери конкретні
файли/модулі з key_modules які потрібні (не весь репо).

ВАЖЛИВО про license_compatibility:
- Якщо є GPL/AGPL — позначити як ризик для комерційного SaaS
- Якщо змішуєш GPL + permissive — результат буде GPL (попередь)
- Якщо ліцензія невідома — позначити як warning

Відповідай ТІЛЬКИ JSON.

{{
  "task": "оригінальна задача",
  "subtasks": [
    {{
      "id": 1,
      "description": "короткий опис підзадачі",
      "selected_repo": "owner/repo або null",
      "reused_parts": ["модуль auth_jwt: src/auth/jwt.py", "модуль X"],
      "rationale": "чому саме цей модуль (1-2 речення)",
      "alternatives": ["owner/repo-alt"]
    }}
  ],
  "integration_plan": [
    "Крок 1: створити wrapper який оркеструє виклики до module_X та module_Y",
    "Крок 2: ...",
    "Крок 3: glue code у файлі main.py"
  ],
  "gaps": [
    "Підзадача N не покривається жодним з репо — потрібно реалізувати з нуля"
  ],
  "risks": {{
    "license_compatibility": "опис проблем якщо є",
    "dependency_conflicts": "потенційні конфлікти версій",
    "maintenance_risk": "репо X не оновлювалось 2 роки",
    "integration_complexity": "high | medium | low — загальна оцінка"
  }},
  "estimated_effort_days": <число днів на склейку>
}}

Якщо для підзадачі немає підходящого репо у бібліотеці — selected_repo: null, додай у gaps.
Будь чесним: краще gap ніж натягування невідповідного репо.
"""


def _format_candidate(repo: dict) -> str:
    """Один кандидат у форматі для промпту."""
    modules_str = ""
    modules = repo.get("key_modules") or []
    if isinstance(modules, str):
        try:
            modules = json.loads(modules)
        except Exception:
            modules = []
    if modules:
        module_lines = []
        for m in modules[:5]:
            if isinstance(m, dict):
                files = ", ".join(m.get("files", [])[:3])
                module_lines.append(f"  - {m.get('name', '?')} ({files}): {m.get('purpose', '')}")
        if module_lines:
            modules_str = "\n  Модулі:\n" + "\n".join(module_lines)

    return (
        f"### {repo.get('full_name', '?')} ⭐{repo.get('stars', 0):,}\n"
        f"  License: {repo.get('license', '?')} | Status: {repo.get('maintenance_status', '?')}\n"
        f"  Stack: {repo.get('stack', '?')}\n"
        f"  Summary: {repo.get('summary_ua', '')[:200]}\n"
        f"  Capabilities: {', '.join((repo.get('capabilities') or [])[:5])}\n"
        f"  Limitations: {', '.join((repo.get('limitations') or [])[:3])}"
        f"{modules_str}"
    )


def decompose_task(task: str, top_n: int = 10, min_score: float = 5.0,
                   verify: bool = True) -> dict:
    """
    Розкладає задачу на підзадачі та підбирає репо.

    Pipeline:
    1. Семантичний пошук top-N кандидатів з бібліотеки
    2. AI будує план декомпозиції з вибором конкретних модулів
    3. Перевірка license-сумісності
    4. (verify=True) Iterative refinement: верифікація що обіцяні файли існують
    """
    from core.embeddings import semantic_search
    from core.database import get_repo_by_name
    from core.omni_router import router
    from core.licenses import check_compatibility, safe_for_commercial_saas

    # 1. Семантичний пошук
    logger.info(f"🔍 Шукаю топ-{top_n} кандидатів для: '{task[:80]}'")
    candidates = semantic_search(task, limit=top_n, min_score=min_score)
    if not candidates:
        return {
            "task": task,
            "error": "Не знайдено кандидатів. Можливо бібліотека порожня або embeddings не побудовані.",
            "subtasks": [],
        }

    # Підтягуємо повні dossiers + key_modules
    enriched = []
    for c in candidates:
        full = get_repo_by_name(c["full_name"])
        if full:
            full["similarity"] = c.get("similarity")
            enriched.append(full)
        else:
            enriched.append(c)

    # 2. Промпт
    candidates_text = "\n\n".join(_format_candidate(r) for r in enriched)
    prompt = DECOMPOSE_PROMPT.format(task=task, n=len(enriched), candidates=candidates_text)

    logger.info(f"🤖 Будую план декомпозиції через AI...")
    try:
        plan = router.complete_json(prompt)
    except Exception as e:
        logger.error(f"❌ AI помилка: {e}")
        return {"task": task, "error": str(e), "candidates": [r["full_name"] for r in enriched]}

    # 3. License compatibility check
    selected_repos = [
        st.get("selected_repo") for st in plan.get("subtasks", [])
        if st.get("selected_repo")
    ]
    licenses = []
    for full_name in selected_repos:
        r = get_repo_by_name(full_name)
        if r and r.get("license"):
            licenses.append(r["license"])

    compat = check_compatibility(licenses)
    saas_safe, saas_reasons = safe_for_commercial_saas(licenses)

    plan["license_check"] = {
        "licenses": licenses,
        "compatible": compat["compatible"],
        "warnings": compat["warnings"],
        "blockers": compat["blockers"],
        "safe_for_commercial_saas": saas_safe,
        "saas_concerns": saas_reasons,
    }

    # 4. Iterative refinement — верифікуємо що обіцяні файли існують
    if verify:
        from core.verify import verify_plan
        logger.info("🔍 Верифікую файли обіцяні AI...")
        plan = verify_plan(plan)

    return plan


def render_plan_md(plan: dict) -> str:
    """Перетворює plan dict у Markdown звіт."""
    lines = [f"# План декомпозиції: {plan.get('task', '?')[:100]}\n"]

    if plan.get("error"):
        lines.append(f"❌ **Помилка:** {plan['error']}\n")
        return "\n".join(lines)

    # Subtasks
    lines.append("## Підзадачі\n")
    for st in plan.get("subtasks", []):
        repo = st.get("selected_repo") or "❌ нема рішення"
        lines.append(f"### {st.get('id', '?')}. {st.get('description', '?')}")
        lines.append(f"- **Репо:** [{repo}](https://github.com/{repo})" if st.get("selected_repo") else f"- **Репо:** {repo}")
        if st.get("reused_parts"):
            lines.append(f"- **Що беремо:** {', '.join(st['reused_parts'])}")
        if st.get("rationale"):
            lines.append(f"- **Чому:** {st['rationale']}")
        if st.get("alternatives"):
            lines.append(f"- **Альтернативи:** {', '.join(st['alternatives'])}")
        # Verification info
        ver = st.get("verification") or {}
        if ver.get("status"):
            status_emoji = {
                "verified": "✅",
                "partial": "⚠️",
                "hallucinated": "❌",
                "no_paths_to_verify": "❓",
                "no_repo": "—",
            }.get(ver["status"], "❓")
            lines.append(f"- **Верифікація:** {status_emoji} {ver['status']} (confidence: {ver.get('confidence', 0)})")
            if ver.get("missing"):
                lines.append(f"  - 🚫 Не існує: `{', '.join(ver['missing'])}`")
            if ver.get("verified"):
                lines.append(f"  - ✓ Підтверджено: `{', '.join(ver['verified'])}`")
        lines.append("")

    # Integration plan
    if plan.get("integration_plan"):
        lines.append("## План інтеграції\n")
        for i, step in enumerate(plan["integration_plan"], 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    # Gaps
    if plan.get("gaps"):
        lines.append("## Прогалини (треба з нуля)\n")
        for g in plan["gaps"]:
            lines.append(f"- {g}")
        lines.append("")

    # Risks
    risks = plan.get("risks") or {}
    if risks:
        lines.append("## Ризики\n")
        for k, v in risks.items():
            if v:
                lines.append(f"- **{k}:** {v}")
        lines.append("")

    # License check
    lc = plan.get("license_check") or {}
    if lc:
        lines.append("## Перевірка ліцензій\n")
        lines.append(f"- Ліцензії: {', '.join(lc.get('licenses', [])) or '—'}")
        lines.append(f"- Сумісні: {'✅ так' if lc.get('compatible') else '❌ ні'}")
        lines.append(f"- Безпечно для комерційного SaaS: {'✅ так' if lc.get('safe_for_commercial_saas') else '⚠️ ні'}")
        if lc.get("warnings"):
            lines.append("- **⚠️ Попередження:**")
            for w in lc["warnings"]:
                lines.append(f"  - {w}")
        if lc.get("blockers"):
            lines.append("- **🚫 Блокери:**")
            for b in lc["blockers"]:
                lines.append(f"  - {b}")
        if lc.get("saas_concerns"):
            lines.append("- **SaaS ризики:**")
            for c in lc["saas_concerns"]:
                lines.append(f"  - {c}")
        lines.append("")

    # Verification summary
    vs = plan.get("verification_summary") or {}
    if vs:
        lines.append("## Верифікація (iterative refinement)\n")
        lines.append(f"- **Загальна довіра:** {vs.get('overall_confidence', 0)} ({vs.get('verified_paths', 0)}/{vs.get('total_paths_checked', 0)} файлів існує)")
        if vs.get("hallucinated_subtasks"):
            lines.append("- **🚫 Підзадачі з вигаданими файлами:**")
            for h in vs["hallucinated_subtasks"]:
                lines.append(f"  - #{h['subtask_id']} ({h['repo']}): {', '.join(h.get('missing', []))}")
        lines.append("")

    if plan.get("estimated_effort_days"):
        lines.append(f"\n**Оцінка склейки:** ~{plan['estimated_effort_days']} днів")

    return "\n".join(lines)
