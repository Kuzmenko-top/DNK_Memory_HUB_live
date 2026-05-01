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


def rank_repos(repos: list[dict]) -> list[dict]:
    """Сортує репозиторії за DNK Score (від найвищого)."""
    for repo in repos:
        repo["dnk_total_score"] = compute_score(repo)

    ranked = sorted(repos, key=lambda r: r.get("dnk_total_score", 0), reverse=True)
    for i, repo in enumerate(ranked, 1):
        repo["rank"] = i

    logger.success(f"✅ Ranked {len(ranked)} repos. Top: {ranked[0].get('full_name', '?')} ({ranked[0].get('dnk_total_score', 0)})" if ranked else "No repos to rank")
    return ranked
