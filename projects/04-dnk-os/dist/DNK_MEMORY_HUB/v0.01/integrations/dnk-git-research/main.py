#!/usr/bin/env python3
"""DNK Git Research CLI — пошук і аналіз GitHub-репозиторіїв"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent))

app = typer.Typer(
    name="dnk-git-research",
    help="🔱 DNK Git Research — GitHub пошук для VibeCoding-підприємців",
    rich_markup_mode="rich",
)
console = Console()


@app.command("search")
def cmd_search(
    query: str = typer.Argument(..., help="Пошуковий запит"),
    top: int = typer.Option(10, "--top", "-n"),
    language: str = typer.Option(None, "--lang", "-l"),
    min_stars: int = typer.Option(10, "--stars"),
    no_analyze: bool = typer.Option(False, "--no-analyze"),
    do_save: bool = typer.Option(False, "--save", "-s"),
):
    """🔍 Пошук репозиторіїв на GitHub"""
    from src.search import search_repos
    from src.ranker import rank_repos
    from src.report import generate_report, save_report
    from src.storage import save_to_library

    console.print(Panel(f"[bold cyan]🔍 Шукаємо: [yellow]{query}[/yellow][/bold cyan]", border_style="blue"))
    repos = search_repos(query, max_results=top, language=language, min_stars=min_stars)
    if not repos:
        console.print("[red]❌ Нічого не знайдено[/red]")
        raise typer.Exit(1)

    if not no_analyze:
        console.print(f"\n[cyan]🤖 AI-аналіз {len(repos)} репозиторіїв...[/cyan]")
        from src.analyzer import analyze_batch
        repos = analyze_batch(repos, with_readme=True)

    repos = rank_repos(repos)

    table = Table(title=f"GitHub Research: {query}", show_lines=True, border_style="blue")
    table.add_column("#", style="dim", width=4)
    table.add_column("Репозиторій", style="cyan")
    table.add_column("⭐", justify="right", style="yellow")
    table.add_column("Score", justify="right", style="green bold")
    table.add_column("Stack / Tech", style="white")
    table.add_column("Складність", justify="center")

    for repo in repos[:top]:
        score_val = repo.get("dnk_total_score") or 0
        stack = (
            ", ".join(repo.get("tech_stack", [])[:3])
            or repo.get("stack", "")
            or repo.get("language", "?")
            or "?"
        )
        difficulty = repo.get("integration_difficulty", "—") if not no_analyze else "—"
        table.add_row(
            str(repo.get("rank", "—")),
            repo.get("full_name") or repo.get("name", "?"),
            f"{repo.get('stars', 0):,}",
            f"{score_val:.1f}",
            stack[:35],
            difficulty[:15],
        )
    console.print(table)

    if do_save:
        save_to_library(repos)
        console.print(f"[green]✅ Збережено {len(repos)} репо в бібліотеку[/green]")

    if not no_analyze:
        report = generate_report(repos, topic=query)
        path = save_report(report, topic=query)
        console.print(f"[dim]📄 Звіт: {path}[/dim]")


@app.command("analyze")
def cmd_analyze(
    topic: str = typer.Option(..., "--topic", "-t"),
    top: int = typer.Option(10, "--top", "-n"),
    do_save: bool = typer.Option(True, "--save/--no-save"),
    do_report: bool = typer.Option(True, "--report/--no-report"),
    multi_pass: bool = typer.Option(False, "--multi-pass/--full",
                                     help="Швидкий triage + deep dive top-5 (дешевше)"),
    expert: bool = typer.Option(False, "--expert", help="Глибокий експертний аналіз кожного репозиторію"),
):
    """🤖 Повний AI-аналіз по темі"""
    from src.search import search_repos
    from src.analyzer import analyze_batch
    from src.ranker import rank_repos
    from src.report import generate_report, save_report
    from src.storage import save_to_library

    console.print(Panel(f"[bold cyan]🤖 Аналіз: [yellow]{topic}[/yellow][/bold cyan]", border_style="green"))
    with console.status("[cyan]Шукаємо на GitHub..."):
        repos = search_repos(topic, max_results=top, min_stars=5)
    console.print(f"✅ Знайдено {len(repos)} репо. AI-аналіз...")
    
    # Якщо вибрано експертний режим, робимо глибокий аналіз для кожного
    if expert:
        from src.expert_analyst import analyze_repo_expert, save_expert_report
        for i, repo in enumerate(repos, 1):
            console.print(f"[{i}/{len(repos)}] 🧐 Експертний аудит: {repo.get('full_name', '?')}")
            # Отримуємо деталі якщо їх немає
            parts = (repo.get("full_name", "") or "").split("/")
            if len(parts) == 2:
                from src.search import get_repo_details, get_repo_tree, get_repo_deep_context
                owner, name = parts[0], parts[1]
                if not repo.get("readme_text"):
                    d = get_repo_details(owner, name)
                    if d: repo.update(d)
                if not repo.get("tree_text"):
                    repo["tree_text"] = get_repo_tree(owner, name)
                if not repo.get("deep_context"):
                    repo["deep_context"] = get_repo_deep_context(owner, name, repo.get("tree_text", ""))
            
            expert_report = analyze_repo_expert(repo)
            report_path = save_expert_report(repo.get("full_name", "unknown"), expert_report)
            console.print(f"   [dim]Звіт збережено: {report_path}[/dim]")
            # Також робимо звичайний аналіз для бази даних
            analysis = analyze_batch([repo], with_readme=True)[0]
            repos[i-1].update(analysis)
    else:
        repos = analyze_batch(repos, with_readme=True, multi_pass=multi_pass)
    repos = rank_repos(repos)
    if do_save:
        save_to_library(repos)
        from src.report import append_to_audit_table
        for r in repos:
            append_to_audit_table(r)
    if do_report:
        content = generate_report(repos, topic)
        path = save_report(content, topic)
        console.print(f"\n[green]📄 Звіт: {path}[/green]")
    if repos:
        best = repos[0]
        score = best.get("dnk_total_score", 0) or 0
        console.print(f"\n[bold green]🏆 Топ: {best.get('full_name', '?')} (Score: {score:.1f})[/bold green]")


@app.command("add")
def cmd_add(
    url: str = typer.Option(..., "--url", "-u", help="URL GitHub репозиторію"),
    expert: bool = typer.Option(False, "--expert", help="Глибокий експертний аналіз"),
):
    """💾 Зберегти конкретний репозиторій"""
    from src.search import get_repo_details
    from src.analyzer import analyze_repo
    from src.ranker import compute_score
    from src.storage import save_to_library

    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        console.print("[red]❌ Невірний URL[/red]")
        raise typer.Exit(1)

    owner, repo_name = parts[0], parts[1]
    console.print(f"[cyan]🔍 {owner}/{repo_name}...[/cyan]")
    from src.search import (
        get_repo_details, get_repo_tree, get_repo_tree_data,
        get_repo_deep_context, get_repo_languages, get_repo_releases,
        get_repo_contributors_count, detect_structural_signals,
    )
    repo = get_repo_details(owner, repo_name)
    if not repo:
        console.print("[red]❌ Не знайдено[/red]")
        raise typer.Exit(1)

    # 1. Tree (для AI display + структурних сигналів)
    tree_items, _ = get_repo_tree_data(owner, repo_name)
    tree_paths = [i["path"] for i in tree_items]
    repo["tree_text"] = get_repo_tree(owner, repo_name)
    repo.update(detect_structural_signals(tree_paths))

    # 2. Розширені метадані (паралельні API виклики)
    console.print("[cyan]📦 Витягую розширені метадані (releases/languages/contributors)...[/cyan]")
    repo["languages_breakdown"] = get_repo_languages(owner, repo_name)
    releases = get_repo_releases(owner, repo_name)
    repo["latest_release_tag"] = releases.get("latest_tag")
    repo["latest_release_date"] = releases.get("latest_date")
    repo["release_cadence_days"] = releases.get("cadence_days")
    repo["contributors_count"] = get_repo_contributors_count(owner, repo_name)

    # 3. Deep context для AI
    console.print("[cyan]🧬 Витягую залежності, конфіги, документацію, entrypoints...[/cyan]")
    repo["deep_context"] = get_repo_deep_context(owner, repo_name, repo["tree_text"])

    analysis = analyze_repo(repo)
    repo.update(analysis)
    repo["dnk_total_score"] = compute_score(repo)
    
    if expert:
        from src.expert_analyst import analyze_repo_expert, save_expert_report
        expert_report = analyze_repo_expert(repo)
        report_path = save_expert_report(repo.get("full_name", "unknown"), expert_report)
        console.print(f"[green]🧐 Експертний звіт збережено: {report_path}[/green]")

    save_to_library([repo])
    
    from src.report import append_to_audit_table
    append_to_audit_table(repo)
    
    score = repo.get("dnk_total_score") or 0
    console.print(f"[green]✅ Збережено: {owner}/{repo_name} | Score: {score:.1f}[/green]")


@app.command("library")
def cmd_library(
    stats: bool = typer.Option(False, "--stats"),
    domain: str = typer.Option(None, "--domain", "-d"),
):
    """📚 Переглянути бібліотеку"""
    from src.storage import get_library_stats, load_library

    if stats:
        s = get_library_stats()
        domains_str = "\n".join([f"  {k}: {v}" for k, v in s.get("domains", {}).items()])
        top5_str = "\n".join([f"  {r['name']} — {r['score']}" for r in s.get("top5", [])])
        console.print(Panel(
            f"[bold]Всього репо: [cyan]{s['total']}[/cyan]\n"
            f"Оновлено: [dim]{s['last_updated']}[/dim]\n\n"
            f"[bold]Домени:[/bold]\n{domains_str}\n\n"
            f"[bold]Top-5:[/bold]\n{top5_str}",
            title="📊 Library Stats", border_style="blue"
        ))
        return

    lib = load_library()
    repos = list(lib.get("repos", {}).values())
    if domain:
        repos = [r for r in repos if r.get("domain") == domain]
    repos.sort(key=lambda r: (r.get("dnk_total_score") or 0), reverse=True)

    table = Table(title="📚 DNK Library", border_style="blue")
    table.add_column("Score", style="green bold", width=7)
    table.add_column("Репозиторій", style="cyan")
    table.add_column("Domain", style="yellow")
    table.add_column("Що робить")
    for r in repos[:20]:
        score = r.get("dnk_total_score") or 0
        what = (r.get("what_it_does") or r.get("summary_ua") or r.get("description") or "—")[:60]
        table.add_row(f"{score:.1f}", r.get("full_name") or "?", r.get("domain", "other"), what)
    console.print(table)


@app.command("find")
def cmd_find(
    query: str = typer.Argument(...),
    domain: str = typer.Option(None, "--domain", "-d"),
    min_score: float = typer.Option(0, "--min-score"),
):
    """🔎 Пошук в локальній бібліотеці"""
    from src.storage import search_library
    results = search_library(query, domain=domain, min_score=min_score)
    if not results:
        console.print(f"[yellow]Нічого не знайдено для: '{query}'[/yellow]")
        console.print(f"[dim]Спробуй: python main.py search '{query}' --save[/dim]")
        return
    console.print(f"[green]✅ Знайдено {len(results)} репозиторіїв[/green]\n")
    for r in results:
        score = r.get("dnk_total_score") or 0
        what = (r.get("what_it_does") or r.get("summary_ua") or r.get("description") or "")[:80]
        console.print(f"[green]{score:.1f}[/green] {r.get('full_name', '?')} ⭐{r.get('stars', 0):,} | {what}")


@app.command("harmonize")
def cmd_harmonize(
    path: str = typer.Option("data", "--path", "-p", help="Папка для очищення")
):
    """🧬 DNK Brain Hygiene — нормалізація MD файлів та ID"""
    from src.orchestrator import BrainOrchestrator
    orchestrator = BrainOrchestrator(os.getcwd())
    
    # Target common data folders
    targets = ["data/reports", "data/DNK_Repo_AUDIT"]
    if path != "data":
        targets.append(path)
        
    with console.status("[cyan]Запуск гігієни мозку (Orchestrator)..."):
        stats = orchestrator.run_hygiene(targets)
        
    console.print(Panel(
        f"[bold green]Гігієна завершена![/bold green]\n\n"
        f"Оброблено файлів: [cyan]{stats['sanitized']}[/cyan]\n"
        f"Виправлено IDs: [cyan]{stats['ids_fixed']}[/cyan]",
        title="🧬 Orchestrator Stats", border_style="green"
    ))


@app.command("decompose")
def cmd_decompose(
    task: str = typer.Argument(..., help="Опис задачі для декомпозиції"),
    top: int = typer.Option(10, "--top", "-n", help="К-сть кандидатів з бібліотеки"),
    min_score: float = typer.Option(5.0, "--min-score", help="Мін DNK Score кандидатів"),
    save: bool = typer.Option(True, "--save/--no-save", help="Зберегти MD-звіт"),
    verify: bool = typer.Option(True, "--verify/--no-verify",
                                help="Перевірити що обіцяні файли існують"),
):
    """🧩 Розкласти задачу на підзадачі та підібрати репо/модулі"""
    from core.decompose import decompose_task, render_plan_md
    import json as _json

    console.print(Panel(
        f"[bold cyan]🧩 Декомпозиція задачі[/bold cyan]\n[yellow]{task}[/yellow]",
        border_style="magenta",
    ))

    with console.status("[cyan]Будую план..."):
        plan = decompose_task(task, top_n=top, min_score=min_score, verify=verify)

    if plan.get("error"):
        console.print(f"[red]❌ {plan['error']}[/red]")
        raise typer.Exit(1)

    md = render_plan_md(plan)
    console.print(md)

    if save:
        from pathlib import Path
        from datetime import datetime, timezone
        slug = "_".join(task.lower().split()[:5])[:50]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = Path("data/decomposition_plans") / f"{ts}_{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        json_path = path.with_suffix(".json")
        json_path.write_text(_json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"\n[green]💾 План збережено:[/green] {path}")


@app.command("recipe")
def cmd_recipe(
    repo: str = typer.Argument(..., help="owner/name або URL репозиторію"),
    project: str = typer.Option("", "--project", "-p", help="Опис вашого проєкту для контексту"),
    save: bool = typer.Option(True, "--save/--no-save"),
):
    """🍳 Згенерувати Integration Recipe для конкретного репо"""
    from src.storage import load_library
    from src.analyzer import generate_integration_recipe
    import json as _json

    repo_key = repo.replace("https://github.com/", "").rstrip("/")
    library = load_library()
    repo_data = library.get("repos", {}).get(repo_key)

    if not repo_data:
        console.print(f"[yellow]⚠️ Репо '{repo_key}' не в бібліотеці. Спочатку: python main.py add --url {repo}[/yellow]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold cyan]🍳 Integration Recipe[/bold cyan]\n"
        f"Репо: [yellow]{repo_key}[/yellow]\n"
        f"Проєкт: [dim]{project or 'не вказано'}[/dim]",
        border_style="green",
    ))

    with console.status("[cyan]Генерую рецепт..."):
        recipe = generate_integration_recipe(repo_data, user_project=project)

    if recipe.get("error"):
        console.print(f"[red]❌ {recipe['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]{recipe.get('verdict', '?')}[/bold] — {recipe.get('verdict_reason', '')}")
    console.print(f"⏱ Оцінка: {recipe.get('estimated_hours', '?')} годин\n")

    if recipe.get("what_to_take"):
        console.print("[cyan]✅ Що взяти:[/cyan]")
        for item in recipe["what_to_take"]:
            console.print(f"  • {item}")

    if recipe.get("dependency_conflicts"):
        console.print("\n[yellow]⚠️ Конфлікти:[/yellow]")
        for c in recipe["dependency_conflicts"]:
            console.print(f"  • {c}")

    if recipe.get("claude_code_prompts"):
        console.print("\n[bold green]🤖 3 промпти для Claude Code:[/bold green]")
        for i, p in enumerate(recipe["claude_code_prompts"], 1):
            console.print(f"\n[dim]Prompt {i}:[/dim]")
            console.print(f"  {p}")

    if save:
        from pathlib import Path
        from datetime import datetime, timezone
        slug = repo_key.replace("/", "_")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = Path("data/recipes") / f"{ts}_{slug}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps(recipe, ensure_ascii=False, indent=2))
        console.print(f"\n[green]💾 Рецепт збережено: {path}[/green]")


@app.command("mcp")
def cmd_mcp(
    port: int = typer.Option(8000, "--port", "-p", help="Порт для MCP сервера (інспектор)"),
):
    """🚀 Запуск MCP сервера для AI-агентів"""
    from mcp_server.server import mcp
    console.print(Panel(
        f"[bold green]🚀 DNK Git Research MCP Server Active[/bold green]\n"
        f"Інтерфейс: [cyan]FastMCP[/cyan]\n"
        f"Локальний доступ: [yellow]Stdio (за замовчуванням)[/yellow]",
        title="MCP Service", border_style="green"
    ))
    mcp.run()


if __name__ == "__main__":
    app()
