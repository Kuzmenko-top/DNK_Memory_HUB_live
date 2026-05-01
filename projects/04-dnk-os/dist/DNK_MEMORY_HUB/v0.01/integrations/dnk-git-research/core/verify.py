"""
verify.py — Iterative refinement: перевірка що обіцяні AI модулі/файли справді існують.
Після AI декомпозиції ходимо в кожне репо і верифікуємо файли через GitHub API.
"""
from __future__ import annotations
import re
from loguru import logger


# Регекс для path-like рядків: src/foo/bar.py, libs/auth/middleware.ts тощо
_PATH_PATTERN = re.compile(
    r"(?:^|[\s,(\"'`])([\w./\-]+/[\w./\-]+\.[a-z]{1,5}|[\w\-]+\.(?:py|ts|js|tsx|jsx|go|rs|rb|java|kt|md|toml|yml|yaml))",
    re.IGNORECASE,
)


def extract_paths(text: str) -> list[str]:
    """Витягти path-подібні рядки з тексту (наприклад з reused_parts)."""
    if not text:
        return []
    matches = _PATH_PATTERN.findall(text)
    # Унікалізуємо, відкидаємо дуже короткі
    seen = set()
    result = []
    for m in matches:
        clean = m.strip(".,()\"'`").strip()
        if len(clean) > 3 and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def verify_files_exist(owner: str, repo: str, paths: list[str]) -> dict:
    """
    Перевіряє які з paths реально існують у репозиторії.
    Повертає {exists: [...], missing: [...]}.
    """
    from src.search import get_repo_file
    exists = []
    missing = []
    for path in paths:
        # head_only через get_repo_file (1 запит на файл)
        content = get_repo_file(owner, repo, path, max_chars=100)
        if content is not None:
            exists.append(path)
        else:
            missing.append(path)
    return {"exists": exists, "missing": missing}


def verify_subtask(subtask: dict) -> dict:
    """
    Верифікує одну підзадачу плану декомпозиції.
    Додає поле 'verification' з результатами.
    """
    full_name = subtask.get("selected_repo")
    if not full_name or "/" not in full_name:
        return {**subtask, "verification": {"status": "no_repo", "verified": [], "missing": []}}

    owner, repo = full_name.split("/", 1)

    # Збираємо всі path-like рядки з reused_parts + key_modules
    reused = subtask.get("reused_parts") or []
    if isinstance(reused, list):
        text_blob = " ".join(str(r) for r in reused)
    else:
        text_blob = str(reused)
    paths = extract_paths(text_blob)

    if not paths:
        return {**subtask, "verification": {
            "status": "no_paths_to_verify",
            "verified": [],
            "missing": [],
            "note": "AI не вказав конкретних шляхів — verifier нема що перевіряти",
        }}

    logger.info(f"🔍 Перевіряю {len(paths)} шляхів у {full_name}...")
    result = verify_files_exist(owner, repo, paths)

    confidence = (
        len(result["exists"]) / len(paths) if paths else 0
    )
    status = "verified" if not result["missing"] else (
        "partial" if result["exists"] else "hallucinated"
    )

    return {
        **subtask,
        "verification": {
            "status": status,            # verified | partial | hallucinated | no_paths_to_verify
            "confidence": round(confidence, 2),
            "verified": result["exists"],
            "missing": result["missing"],
        }
    }


def verify_plan(plan: dict) -> dict:
    """
    Верифікує всі підзадачі плану.
    Додає сумарне поле 'verification_summary' до плану.
    """
    if not plan.get("subtasks"):
        return plan

    verified_subtasks = []
    total_paths = 0
    total_verified = 0
    hallucinations = []

    for st in plan["subtasks"]:
        v = verify_subtask(st)
        verified_subtasks.append(v)
        ver = v.get("verification") or {}
        total_paths += len(ver.get("verified", [])) + len(ver.get("missing", []))
        total_verified += len(ver.get("verified", []))
        if ver.get("status") == "hallucinated":
            hallucinations.append({
                "subtask_id": v.get("id"),
                "repo": v.get("selected_repo"),
                "missing": ver.get("missing"),
            })

    plan["subtasks"] = verified_subtasks
    plan["verification_summary"] = {
        "overall_confidence": round(total_verified / total_paths, 2) if total_paths else 0,
        "total_paths_checked": total_paths,
        "verified_paths": total_verified,
        "missing_paths": total_paths - total_verified,
        "hallucinated_subtasks": hallucinations,
    }

    # Підвищуємо ризики при галюцінаціях
    if hallucinations:
        risks = plan.get("risks") or {}
        risks["hallucination_risk"] = (
            f"AI вказав {len(hallucinations)} підзадач(і) з неіснуючими файлами. "
            "Перевір 'verification.missing' у subtasks і не довіряй reused_parts наосліп."
        )
        plan["risks"] = risks

    return plan
