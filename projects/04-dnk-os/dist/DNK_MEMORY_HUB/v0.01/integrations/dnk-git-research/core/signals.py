"""
signals.py — Похідні сигнали (Шар 2)
Розраховує newness_score, maintenance_status, popularity_tier на основі сирих метаданих.
"""
from __future__ import annotations
import math
from datetime import datetime


def compute_newness_score(created_at: str | None, days_since_push: int | None) -> float:
    """
    Newness 0-1: 1.0 = свіжий проєкт (< 1 рік), 0 = дуже старий (10+ років).
    Враховує і вік, і активність.
    """
    if not created_at:
        return 0.5
    try:
        age_days = (datetime.utcnow() - datetime.strptime(created_at[:10], "%Y-%m-%d")).days
    except Exception:
        return 0.5
    age_years = age_days / 365
    # Логарифмічна шкала: 1 рік = 0.8, 5 років = 0.4, 10+ років = 0.1
    age_component = max(0.0, 1.0 - math.log10(age_years + 1) * 0.5)
    # Якщо давно не оновлювали — знижуємо
    activity_penalty = 0.0
    if days_since_push is not None and days_since_push > 365:
        activity_penalty = min(0.3, (days_since_push - 365) / 365 * 0.1)
    return round(max(0.0, min(1.0, age_component - activity_penalty)), 2)


def compute_maintenance_status(repo: dict) -> str:
    """
    active | maintained | dormant | abandoned
    На основі pushed_at, release_cadence, archived.
    """
    if repo.get("archived"):
        return "abandoned"
    days = repo.get("days_since_push")
    cadence = repo.get("release_cadence_days")
    if days is None:
        return "dormant"
    if days <= 30:
        return "active"
    if days <= 180:
        return "maintained"
    if days <= 540:  # 1.5 роки
        # Якщо релізи виходили регулярно — "maintained" зі знижкою
        if cadence and cadence < 180:
            return "maintained"
        return "dormant"
    return "abandoned"


def compute_popularity_tier(stars: int, age_years: float | None) -> str:
    """
    viral | popular | niche | obscure.
    Враховує вік репо: 1k зірок за 1 рік ≠ 1k за 5 років.
    """
    if not stars:
        return "obscure"
    # Stars per year
    spy = stars / max(0.5, age_years) if age_years else stars
    if spy >= 5000 or stars >= 50000:
        return "viral"
    if spy >= 500 or stars >= 5000:
        return "popular"
    if spy >= 50 or stars >= 500:
        return "niche"
    return "obscure"


def enrich_with_signals(repo: dict) -> dict:
    """
    Додає до repo похідні сигнали: newness_score, maintenance_status, popularity_tier.
    Не модифікує оригінал.
    """
    enriched = dict(repo)
    age_years = None
    if repo.get("created_at"):
        try:
            age_days = (datetime.utcnow() - datetime.strptime(repo["created_at"][:10], "%Y-%m-%d")).days
            age_years = age_days / 365
        except Exception:
            pass

    enriched["newness_score"] = compute_newness_score(
        repo.get("created_at"), repo.get("days_since_push")
    )
    enriched["maintenance_status"] = compute_maintenance_status(repo)
    enriched["popularity_tier"] = compute_popularity_tier(
        repo.get("stars", 0), age_years
    )

    # License permissions
    from core.licenses import get_permissions
    enriched["license_permissions"] = get_permissions(repo.get("license", ""))

    return enriched
