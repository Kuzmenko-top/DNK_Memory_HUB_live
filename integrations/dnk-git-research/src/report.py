"""
report.py — Markdown Report Generator
Генерація звітів по темах для VibeCoding-підприємців
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from loguru import logger


RECOMMENDATION_EMOJI = {
    "✅ Рекомендовано": "✅",
    "🟡 Можна розглянути": "🟡",
    "❌ Не підходить": "❌",
    "❓ Без оцінки": "❓",
}


def generate_report(repos: list[dict], topic: str, format: str = "markdown") -> str:
    """Генерує звіт у вказаному форматі."""
    if format == "markdown":
        return _markdown_report(repos, topic)
    elif format == "table":
        return _table_report(repos, topic)
    return _markdown_report(repos, topic)


def _markdown_report(repos: list[dict], topic: str) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# 🔍 DNK Git Research: `{topic}`",
        f"> Згенеровано: {now} | Знайдено: {len(repos)} репозиторіїв",
        "",
        "---",
        "",
        "## 📊 TOP Репозиторії (по DNK Score)",
        "",
        "| # | Репозиторій | ⭐ Stars | 🎯 DNK Score | Stack | Складність | Статус |",
        "|---|---|---|---|---|---|---|",
    ]

    for repo in repos[:15]:
        rank = repo.get("rank", "—")
        name = repo.get("full_name") or repo.get("name", "?")
        url = repo.get("url", "#")
        stars = f"{repo.get('stars', 0):,}"
        score = repo.get("dnk_total_score", 0)
        stack = (repo.get("stack", "") or "")[:40]
        complexity = repo.get("integration_complexity", "?")
        rec = repo.get("recommendation", "❓")
        emoji = RECOMMENDATION_EMOJI.get(rec, "❓")

        lines.append(
            f"| {rank} | [{name}]({url}) | {stars} | **{score}** | {stack} | {complexity} | {emoji} |"
        )

    lines += ["", "---", "", "## 🔎 Детальний аналіз", ""]

    for repo in repos[:10]:
        name = repo.get("full_name") or repo.get("name", "?")
        url = repo.get("url", "#")
        stars = repo.get("stars", 0)
        score = repo.get("dnk_total_score", 0)
        fit_score = repo.get("dnk_fit_score", 0)
        days = repo.get("days_since_push", "?")

        lines += [
            f"### {repo.get('rank', '')}. [{name}]({url})",
            f"**⭐ {stars:,} stars** | **🎯 DNK Score: {score}/10** | 🤖 AI Fit: {fit_score}/10 | 📅 {days} днів тому",
            "",
            f"**📝 Опис:** {repo.get('description', '—')}",
            "",
        ]

        summary = repo.get("summary_ua", "")
        if summary:
            lines += [f"**🇺🇦 Підсумок:** {summary}", ""]

        use_cases = repo.get("use_cases", [])
        if use_cases:
            lines += ["**💼 Use Cases:**"]
            for uc in use_cases[:3]:
                lines.append(f"- {uc}")
            lines.append("")

        fit_reason = repo.get("dnk_fit_reason", "")
        if fit_reason:
            lines += [f"**🎯 DNK Fit:** {fit_reason}", ""]

        integration = repo.get("integration_notes", "")
        if integration:
            lines += [f"**⚙️ Інтеграція ({repo.get('integration_complexity', '?')}):** {integration}", ""]

        lines += [
            f"🏷️ `{repo.get('language', '?')}` | 📄 `{repo.get('license', '?')}` | {repo.get('recommendation', '❓')}",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def _table_report(repos: list[dict], topic: str) -> str:
    """Короткий табличний вивід для термінала."""
    from rich.table import Table
    from rich.console import Console
    import io

    table = Table(title=f"GitHub Research: {topic}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Репозиторій", style="cyan", no_wrap=True)
    table.add_column("⭐", justify="right")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Stack", style="yellow")
    table.add_column("Rec", justify="center")

    for repo in repos[:20]:
        table.add_row(
            str(repo.get("rank", "—")),
            repo.get("full_name") or repo.get("name", "?"),
            f"{repo.get('stars', 0):,}",
            f"{repo.get('dnk_total_score', 0)}",
            (repo.get("stack", "") or "")[:30],
            repo.get("recommendation", "❓")[:2],
        )

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False)
    console.print(table)
    return buf.getvalue()


def save_report(content: str, topic: str, output_dir: str = "data/reports") -> Path:
    """Зберегти звіт у файл."""
    safe_topic = topic.replace(" ", "_").replace("/", "-")[:50]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}_{safe_topic}.md"

    out_dir = Path(__file__).parent.parent / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.success(f"📄 Report saved: {path}")
    return path


def append_to_audit_table(repo: dict, table_path: str = "data/catalog.md"):
    """Додає або оновлює запис у центральній таблиці аудиту."""
    path = Path(__file__).parent.parent / table_path
    if not path.exists():
        logger.warning(f"Таблиця аудиту не знайдена за шляхом: {path}")
        return

    category = repo.get("domain", "Uncategorized")
    name = repo.get("full_name") or repo.get("name", "?")
    url = repo.get("url", "#")
    desc = (repo.get("summary_ua") or repo.get("description") or "—").replace("\n", " ").strip()[:100]
    
    role = (repo.get("dnk_fit_reason", "—")).replace("\n", " ").strip()[:50]
    potential = str(repo.get("dnk_fit_score", "?"))
    complexity = str(repo.get("integration_complexity", "?")).replace("\n", "")
    
    rec_text = repo.get("recommendation", "❓")
    rec = RECOMMENDATION_EMOJI.get(rec_text, rec_text)
    
    row = f"| **{category}** | [{name}]({url}) | {desc} | {role} | {potential} | {complexity} | {rec} | New |\n"
    
    with open(path, "a", encoding="utf-8") as f:
        f.write(row)
    
    logger.success(f"✅ Додано {name} у таблицю аудиту.")
