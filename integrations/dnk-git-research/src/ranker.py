"""
ranker.py — DNK Fit Scoring Module
Розрахунок фінального Score для ранжування репозиторіїв
"""
from __future__ import annotations
import math
from loguru import logger


def compute_score(repo: dict) -> float:
    """
    Фінальний DNK Score для репо (0.0 - 10.0).

    Weights & Boosters (Legacy Aligned):
      - dnk_fit_score (AI): 40%
      - recent_activity:    20%
      - stars (log scale):  15%
      - readme_quality:     15%
      - [BOOST] GPU/CUDA:   +1.0
      - [BOOST] License:    +1.0
    """
    # 1. AI DNK Fit Score (0-10)
    dnk_fit = min(float(repo.get("dnk_fit_score", 0) or 0), 10.0)

    # 2. Recent Activity Score (0-10)
    days = repo.get("days_since_push")
    if days is None:
        activity = 3.0
    elif days <= 7:
        activity = 10.0
    elif days <= 30:
        activity = 8.5
    elif days <= 90:
        activity = 7.0
    elif days <= 365:
        activity = 4.0
    else:
        activity = 0.5

    # 3. Stars Score (log scale, 0-10)
    stars = repo.get("stars", 0) or 0
    if stars == 0:
        stars_score = 0.0
    elif stars >= 50000:
        stars_score = 10.0
    else:
        stars_score = min(math.log10(stars + 1) / math.log10(50000) * 10, 10.0)

    # 4. README Quality (0-10)
    readme_text = (repo.get("readme_text", "") or "").lower()
    readme_len = len(readme_text)
    readiness = repo.get("readiness", "")
    readme_score = min(readme_len / 200, 8.0)
    if readiness == "production-ready":
        readme_score = min(readme_score + 2, 10.0)
    elif readiness == "beta":
        readme_score = min(readme_score + 1, 10.0)

    # === BOOSTERS (Legacy Gems) ===
    boost = 0.0
    
    # 5. GPU/CUDA Support Boost (+1.0)
    gpu_keywords = ['cuda', 'gpu', 'pytorch', 'onnx', 'tensorrt', 'tlt', 'model-parallel']
    metadata = (repo.get("description", "") + " " + repo.get("name", "") + " " + readme_text).lower()
    if any(k in metadata for k in gpu_keywords):
        boost += 1.0
        
    # 6. Commercial License Boost (+1.0)
    license_key = (repo.get("license", "") or "").lower()
    if any(l in license_key for l in ['mit', 'apache', 'bsd']):
        boost += 1.0

    # Weighted final score
    final = (
        dnk_fit * 0.40 +
        activity * 0.20 +
        stars_score * 0.15 +
        readme_score * 0.15
    ) + boost

    return round(min(final, 10.0), 2)


def compute_friction_score(repo: dict) -> float:
    """
    Integration Friction Score: 0-10, вище = легше інтегрувати.
    Окрема від Total Score — вимірює простоту інтеграції, не якість.

    Якщо AI вже розрахував — повертаємо AI-значення.
    Інакше — евристика з setup_signals.
    """
    ai_friction = (repo.get("integration_friction") or {}).get("score")
    if ai_friction and isinstance(ai_friction, (int, float)) and 0 < ai_friction <= 10:
        return round(float(ai_friction), 2)

    # Евристичний розрахунок з setup_signals
    signals = repo.get("setup_signals") or {}
    score = 5.0  # базовий

    if signals.get("has_dockerfile"):       score += 2.0
    if signals.get("has_docker_compose"):   score += 0.5
    if signals.get("has_env_example"):      score += 2.0
    if signals.get("has_makefile"):         score += 1.0
    if repo.get("has_tests"):               score += 1.5
    if repo.get("has_ci"):                  score += 1.0

    # Penalty за кількість залежностей
    deps = signals.get("direct_deps_count", 0) or 0
    if deps > 5:
        score -= min((deps - 5) / 10, 2.0)

    # License penalty
    license_risk = repo.get("license_risk", "")
    if license_risk == "risky":     score -= 2.0
    elif license_risk == "warning": score -= 1.0

    # Penalty за staleness
    days = repo.get("days_since_push")
    if days and days > 180:
        score -= 1.5

    return round(min(max(score, 0), 10), 2)


def rank_repos(repos: list[dict]) -> list[dict]:
    """Сортує репозиторії за DNK Score. Додає integration_friction як окрему метрику."""
    for repo in repos:
        repo["dnk_total_score"] = compute_score(repo)
        repo["friction_score"] = compute_friction_score(repo)

    ranked = sorted(repos, key=lambda r: r.get("dnk_total_score", 0), reverse=True)
    for i, repo in enumerate(ranked, 1):
        repo["rank"] = i

    if ranked:
        top = ranked[0]
        logger.success(
            f"✅ Ranked {len(ranked)} repos. "
            f"Top: {top.get('full_name', '?')} "
            f"(Score: {top.get('dnk_total_score', 0)}, Friction: {top.get('friction_score', 0)})"
        )
    return ranked
