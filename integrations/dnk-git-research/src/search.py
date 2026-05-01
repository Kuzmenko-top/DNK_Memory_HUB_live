"""
search.py — GitHub API Search Module
"""
from __future__ import annotations
import os
import base64
import httpx
import yaml
from loguru import logger
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


BASE_URL = "https://api.github.com"
_TREE_LIMIT = 300  # макс файлів у tree для AI контексту


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token and token not in ("your_github_token_here", ""):
        headers["Authorization"] = f"Bearer {token}"
        logger.debug("🔑 GitHub Token active (5000 req/h)")
    else:
        logger.warning("⚠️ No GitHub Token — limited to 60 req/h")
    return headers


def search_repos(
    query: str,
    max_results: int | None = None,
    language: str | None = None,
    min_stars: int = 0,
    days_since_push: int | None = None,
    sort: str = "stars",
) -> list[dict]:
    """Пошук репозиторіїв за запитом."""
    cfg = _load_config()
    max_results = max_results or cfg["search"]["max_results"]

    q_parts = [query]
    if language:
        q_parts.append(f"language:{language}")
    if min_stars > 0:
        q_parts.append(f"stars:>={min_stars}")
    if days_since_push:
        cutoff = (datetime.utcnow() - timedelta(days=days_since_push)).strftime("%Y-%m-%d")
        q_parts.append(f"pushed:>={cutoff}")

    full_query = " ".join(q_parts)
    logger.info(f"🔍 GitHub query: '{full_query}'")

    results = []
    page = 1
    per_page = min(30, max_results)

    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=30) as client:
        while len(results) < max_results:
            try:
                resp = client.get(
                    f"{BASE_URL}/search/repositories",
                    params={"q": full_query, "sort": sort, "order": "desc",
                            "per_page": per_page, "page": page},
                )
            except httpx.TimeoutException:
                logger.warning("⚠️ GitHub search timeout — повертаємо часткові результати")
                break

            if resp.status_code == 403:
                logger.error("❌ GitHub rate limit! Перевір GITHUB_TOKEN у .env")
                break
            if resp.status_code == 422:
                logger.error(f"❌ Невалідний пошуковий запит: {full_query}")
                break
            if resp.status_code != 200:
                logger.error(f"❌ GitHub API {resp.status_code}: {resp.text[:200]}")
                break

            items = resp.json().get("items", [])
            if not items:
                break
            for repo in items:
                results.append(_normalize_repo(repo))
                if len(results) >= max_results:
                    break
            if len(items) < per_page:
                break
            page += 1

    logger.success(f"✅ Знайдено {len(results)} репозиторіїв")
    return results


def get_repo_details(owner: str, repo: str) -> dict | None:
    """Деталі конкретного репозиторію + README."""
    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=30) as client:
        try:
            resp = client.get(f"{BASE_URL}/repos/{owner}/{repo}")
        except httpx.TimeoutException:
            logger.warning(f"⚠️ Timeout при отриманні {owner}/{repo}")
            return None

        if resp.status_code == 404:
            logger.warning(f"⚠️ Репозиторій {owner}/{repo} не знайдено")
            return None
        if resp.status_code != 200:
            logger.error(f"❌ GitHub API {resp.status_code} для {owner}/{repo}")
            return None

        normalized = _normalize_repo(resp.json())

        # README — з безпечним декодуванням
        try:
            readme_resp = client.get(f"{BASE_URL}/repos/{owner}/{repo}/readme")
            if readme_resp.status_code == 200:
                content = readme_resp.json().get("content", "")
                if content:
                    raw_bytes = base64.b64decode(content)
                    # errors="replace" — не впаде на будь-якому кодуванні
                    normalized["readme_text"] = raw_bytes.decode("utf-8", errors="replace")[:4000]
        except Exception as e:
            logger.debug(f"README недоступний для {owner}/{repo}: {e}")

        return normalized


def get_repo_tree_data(owner: str, repo: str, branch: str | None = None) -> tuple[list[dict], bool]:
    """
    Внутрішній API: повертає (tree_items, truncated_flag).
    Без обмеження по кількості файлів — для пошуку у моно-репо.
    """
    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=30) as client:
        if branch is None:
            try:
                resp = client.get(f"{BASE_URL}/repos/{owner}/{repo}")
                branch = resp.json().get("default_branch", "main") if resp.status_code == 200 else "main"
            except Exception:
                branch = "main"

        try:
            resp = client.get(
                f"{BASE_URL}/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"},
            )
        except httpx.TimeoutException:
            return ([], False)

        if resp.status_code == 404 and branch == "main":
            with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=30) as c2:
                r2 = c2.get(f"{BASE_URL}/repos/{owner}/{repo}/git/trees/master",
                            params={"recursive": "1"})
                if r2.status_code != 200:
                    return ([], False)
                d = r2.json()
                return (d.get("tree", []), d.get("truncated", False))
        if resp.status_code != 200:
            return ([], False)
        data = resp.json()
        return (data.get("tree", []), data.get("truncated", False))


def get_repo_tree(owner: str, repo: str, branch: str | None = None) -> str:
    """
    Отримати дерево файлів репозиторію (рекурсивно) у вигляді тексту для AI.
    Обмежено _TREE_LIMIT файлами.
    """
    tree, truncated = get_repo_tree_data(owner, repo, branch)
    if not tree:
        return ""

    root_files = [i for i in tree if "/" not in i.get("path", "") and i["type"] == "blob"]
    dirs = [i for i in tree if i["type"] == "tree"]
    other = [i for i in tree if i not in root_files and i not in dirs]
    ordered = root_files + dirs + other

    lines = [f"{'📁 ' if item['type'] == 'tree' else '📄 '}{item['path']}"
             for item in ordered[:_TREE_LIMIT]]
    if truncated or len(tree) > _TREE_LIMIT:
        lines.append(f"... (репо містить {len(tree)}+ файлів, показано {len(lines)})")
    return "\n".join(lines)


def get_repo_file(owner: str, repo: str, path: str, branch: str | None = None,
                  max_chars: int = 8000) -> str | None:
    """
    Завантажити вміст одного файлу з репо. Повертає текст або None.
    """
    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=20) as client:
        try:
            params = {"ref": branch} if branch else {}
            resp = client.get(f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}", params=params)
        except httpx.TimeoutException:
            return None

        if resp.status_code != 200:
            return None
        data = resp.json()
        if isinstance(data, list):
            return None  # це директорія
        encoding = data.get("encoding", "")
        content = data.get("content", "")
        if not content:
            return None
        if encoding == "base64":
            try:
                raw = base64.b64decode(content)
                return raw.decode("utf-8", errors="replace")[:max_chars]
            except Exception:
                return None
        return content[:max_chars]


# Файли, які ми витягуємо для глибокого AI-аналізу
_DEPENDENCY_FILES = [
    "package.json", "requirements.txt", "pyproject.toml", "setup.py",
    "Cargo.toml", "go.mod", "Gemfile", "composer.json", "pom.xml", "build.gradle",
]

_CONFIG_FILES = [
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "Makefile",
]

_DOC_FILES = [
    "ARCHITECTURE.md", "CONTRIBUTING.md", "ROADMAP.md", "USAGE.md",
    "docs/README.md", "docs/getting-started.md", "docs/architecture.md",
]

_ENTRYPOINT_HINTS = [
    "main.py", "app.py", "server.py", "cli.py", "__main__.py",
    "src/main.py", "src/app.py", "src/index.ts", "src/index.js",
    "index.ts", "index.js", "src/main.rs", "cmd/main.go", "main.go",
]


def _find_in_paths(paths: list[str], filename: str) -> str | None:
    """Знайти файл серед списку шляхів. Повертає найкоротший шлях."""
    target = filename.lower()
    candidates = [p for p in paths
                  if p.lower() == target or p.lower().endswith("/" + target)]
    return min(candidates, key=lambda p: p.count("/")) if candidates else None


def get_repo_deep_context(owner: str, repo: str, tree_text: str = "",
                          branch: str | None = None) -> dict:
    """
    Витягнути курований набір файлів для глибокого AI-аналізу.
    Підтримує монорепо: якщо файл не в корені — шукає у повному tree через API.
    """
    sections: dict[str, list[str]] = {
        "dependencies": [],
        "configs": [],
        "docs": [],
        "entrypoints": [],
    }

    # Отримаємо ПОВНИЙ список шляхів (не обрізаний 300-line limit)
    tree_items, _ = get_repo_tree_data(owner, repo, branch)
    all_paths = [item["path"] for item in tree_items if item.get("type") == "blob"]

    def _fetch_with_fallback(fname: str, max_chars: int) -> tuple[str, str] | None:
        """Спочатку пробуємо корінь, потім шукаємо в повному tree."""
        content = get_repo_file(owner, repo, fname, branch=branch, max_chars=max_chars)
        if content:
            return (fname, content)
        path = _find_in_paths(all_paths, fname)
        if path and path != fname:
            content = get_repo_file(owner, repo, path, branch=branch, max_chars=max_chars)
            if content:
                return (path, content)
        return None

    # Залежності
    for fname in _DEPENDENCY_FILES:
        result = _fetch_with_fallback(fname, max_chars=3000)
        if result:
            actual_path, content = result
            sections["dependencies"].append(f"### {actual_path}\n```\n{content}\n```")

    # Конфіги
    for fname in _CONFIG_FILES:
        result = _fetch_with_fallback(fname, max_chars=2000)
        if result:
            actual_path, content = result
            sections["configs"].append(f"### {actual_path}\n```\n{content}\n```")

    # Доки
    for fname in _DOC_FILES:
        result = _fetch_with_fallback(fname, max_chars=3000)
        if result:
            actual_path, content = result
            sections["docs"].append(f"### {actual_path}\n{content}")

    # Entrypoints — шукаємо за іменем у повному tree
    for fname in _ENTRYPOINT_HINTS:
        path = _find_in_paths(all_paths, fname.split("/")[-1])
        if path:
            content = get_repo_file(owner, repo, path, branch=branch, max_chars=2500)
            if content:
                lines = content.splitlines()[:50]
                sections["entrypoints"].append(
                    f"### {path} (перші 50 рядків)\n```\n" + "\n".join(lines) + "\n```"
                )
                if len(sections["entrypoints"]) >= 3:
                    break

    return {
        "dependencies": "\n\n".join(sections["dependencies"]) or "—",
        "configs": "\n\n".join(sections["configs"]) or "—",
        "docs": "\n\n".join(sections["docs"]) or "—",
        "entrypoints": "\n\n".join(sections["entrypoints"]) or "—",
    }


def get_repo_languages(owner: str, repo: str) -> dict:
    """Languages breakdown у відсотках. {Python: 75.5, JS: 24.5}."""
    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=20) as client:
        try:
            resp = client.get(f"{BASE_URL}/repos/{owner}/{repo}/languages")
            if resp.status_code != 200:
                return {}
            raw = resp.json()
            total = sum(raw.values()) or 1
            return {k: round(v / total * 100, 1) for k, v in raw.items()}
        except Exception:
            return {}


def get_repo_releases(owner: str, repo: str, limit: int = 10) -> dict:
    """
    Останній реліз + середня частота релізів (днів між релізами).
    Повертає: {latest_tag, latest_date, cadence_days}.
    """
    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=20) as client:
        try:
            resp = client.get(
                f"{BASE_URL}/repos/{owner}/{repo}/releases",
                params={"per_page": limit},
            )
            if resp.status_code != 200:
                return {"latest_tag": None, "latest_date": None, "cadence_days": None}
            releases = resp.json()
        except Exception:
            return {"latest_tag": None, "latest_date": None, "cadence_days": None}

    if not releases:
        return {"latest_tag": None, "latest_date": None, "cadence_days": None}

    latest = releases[0]
    latest_date = latest.get("published_at", "") or latest.get("created_at", "")

    cadence = None
    if len(releases) >= 2:
        dates = []
        for r in releases:
            d = r.get("published_at") or r.get("created_at")
            if d:
                try:
                    dates.append(datetime.strptime(d[:10], "%Y-%m-%d"))
                except Exception:
                    pass
        if len(dates) >= 2:
            dates.sort(reverse=True)
            gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
            cadence = int(sum(gaps) / len(gaps))

    return {
        "latest_tag": latest.get("tag_name"),
        "latest_date": latest_date[:10] if latest_date else None,
        "cadence_days": cadence,
    }


def get_repo_contributors_count(owner: str, repo: str) -> int | None:
    """Швидко (per_page=1, читаємо Link header) — кількість контрибуторів."""
    with httpx.Client(headers=_get_headers(), follow_redirects=True, timeout=20) as client:
        try:
            resp = client.get(
                f"{BASE_URL}/repos/{owner}/{repo}/contributors",
                params={"per_page": 1, "anon": "0"},
            )
            if resp.status_code != 200:
                return None
            link = resp.headers.get("Link", "")
            # Якщо є Link header з rel="last" — там номер останньої сторінки = кількість
            import re as _re
            m = _re.search(r'<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="last"', link)
            if m:
                return int(m.group(1))
            # Інакше — всі контрибутори вмістились на одну сторінку
            return len(resp.json())
        except Exception:
            return None


def detect_structural_signals(tree_paths: list[str]) -> dict:
    """
    З tree paths визначаємо: has_tests, has_ci, has_changelog.
    """
    paths_lower = [p.lower() for p in tree_paths]
    has_tests = any(
        p == "tests" or p.startswith("tests/") or p == "test" or p.startswith("test/")
        or p.endswith("_test.py") or p.endswith(".test.ts") or p.endswith(".test.js")
        or p.endswith("_test.go") or p.endswith(".spec.ts")
        for p in paths_lower
    )
    has_ci = any(
        p.startswith(".github/workflows/") or p == ".gitlab-ci.yml"
        or p == ".circleci/config.yml" or p == "azure-pipelines.yml"
        for p in paths_lower
    )
    has_changelog = any(
        p == "changelog.md" or p == "changelog" or p == "history.md"
        or p == "releases.md" or p.startswith("docs/changelog")
        for p in paths_lower
    )
    return {"has_tests": has_tests, "has_ci": has_ci, "has_changelog": has_changelog}


def _normalize_repo(repo: dict) -> dict:
    pushed = repo.get("pushed_at", "") or ""
    days_since = None
    if pushed:
        try:
            dt = datetime.strptime(pushed[:10], "%Y-%m-%d")
            days_since = (datetime.utcnow() - dt).days
        except Exception:
            pass
    owner = repo.get("owner") or {}
    return {
        "id": repo.get("id"),
        "name": repo.get("name", ""),
        "full_name": repo.get("full_name", ""),
        "url": repo.get("html_url", ""),
        "owner_type": owner.get("type", "").lower() if owner else "",  # user | organization
        "description": (repo.get("description") or ""),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "watchers": repo.get("subscribers_count", repo.get("watchers_count", 0)),
        "language": repo.get("language", "") or "",
        "topics": repo.get("topics", []),
        "license": (repo.get("license") or {}).get("spdx_id", "") or "",
        "created_at": (repo.get("created_at", "") or "")[:10],
        "pushed_at": pushed[:10] if pushed else "",
        "days_since_push": days_since,
        "open_issues": repo.get("open_issues_count", 0),
        "archived": repo.get("archived", False),
        "readme_text": "",
    }
