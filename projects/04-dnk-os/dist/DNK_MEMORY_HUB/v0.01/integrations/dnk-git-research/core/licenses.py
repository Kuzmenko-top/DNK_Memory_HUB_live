"""
licenses.py — SPDX license analysis & compatibility checking
Базується на офіційній SPDX-таксономії: https://spdx.org/licenses/
"""
from __future__ import annotations

# Дозволи кожної ліцензії (на основі choosealicense.com та офіційних SPDX).
# Поля: commercial_use, derivative_works, patent_grant, network_use_disclosure,
#       same_license_required (copyleft), source_disclosure_required.
LICENSE_PERMISSIONS: dict[str, dict] = {
    "MIT": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "permissive",
    },
    "Apache-2.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": True, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "permissive",
    },
    "BSD-2-Clause": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "permissive",
    },
    "BSD-3-Clause": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "permissive",
    },
    "ISC": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "permissive",
    },
    "MPL-2.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": True, "network_use_disclosure": False,
        "same_license_required": True, "source_disclosure_required": True,
        "category": "weak-copyleft",
    },
    "LGPL-2.1": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": True, "source_disclosure_required": True,
        "category": "weak-copyleft",
    },
    "LGPL-3.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": True, "network_use_disclosure": False,
        "same_license_required": True, "source_disclosure_required": True,
        "category": "weak-copyleft",
    },
    "GPL-2.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": True, "source_disclosure_required": True,
        "category": "strong-copyleft",
    },
    "GPL-3.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": True, "network_use_disclosure": False,
        "same_license_required": True, "source_disclosure_required": True,
        "category": "strong-copyleft",
    },
    "AGPL-3.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": True, "network_use_disclosure": True,
        "same_license_required": True, "source_disclosure_required": True,
        "category": "network-copyleft",
    },
    "Unlicense": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "public-domain",
    },
    "CC0-1.0": {
        "commercial_use": True, "derivative_works": True,
        "patent_grant": False, "network_use_disclosure": False,
        "same_license_required": False, "source_disclosure_required": False,
        "category": "public-domain",
    },
}


def get_permissions(spdx_id: str) -> dict:
    """Повертає дозволи ліцензії або порожній словник для невідомих."""
    if not spdx_id:
        return {"category": "unknown", "commercial_use": False}
    return LICENSE_PERMISSIONS.get(spdx_id, {"category": "unknown", "commercial_use": False})


def is_commercial_safe(spdx_id: str) -> bool:
    """Чи безпечна ліцензія для комерційного закритого продукту."""
    perms = get_permissions(spdx_id)
    if perms.get("category") in ("permissive", "public-domain", "weak-copyleft"):
        return True
    if perms.get("category") == "unknown":
        return False
    # GPL/AGPL — несумісні із закритим комерційним продуктом
    return False


def check_compatibility(licenses: list[str]) -> dict:
    """
    Перевіряє сумісність набору ліцензій для комбінованого використання.
    Повертає: {compatible: bool, warnings: [...], blockers: [...]}.
    """
    licenses = [l for l in licenses if l]
    if not licenses:
        return {"compatible": True, "warnings": [], "blockers": []}

    warnings: list[str] = []
    blockers: list[str] = []
    categories = [get_permissions(l).get("category", "unknown") for l in licenses]

    # AGPL — будь-яка інша ліцензія має бути сумісна, але AGPL "заражає" мережеві сервіси
    if "network-copyleft" in categories:
        agpl_repos = [l for l, c in zip(licenses, categories) if c == "network-copyleft"]
        warnings.append(
            f"AGPL ({', '.join(agpl_repos)}): якщо використовуєш як SaaS — "
            "потрібно відкрити вихідний код всього сервісу, навіть власних модифікацій."
        )

    # GPL + permissive: можна, але результуючий продукт буде GPL
    has_gpl = "strong-copyleft" in categories or "network-copyleft" in categories
    has_permissive = any(c in ("permissive", "public-domain") for c in categories)
    if has_gpl and has_permissive:
        warnings.append(
            "GPL/AGPL у поєднанні з permissive: результуючий продукт буде під GPL/AGPL "
            "(GPL 'заражає' все що з нею лінкується)."
        )

    # GPL + closed source — блокер
    unknowns = [l for l, c in zip(licenses, categories) if c == "unknown"]
    if unknowns:
        warnings.append(
            f"Невідомі ліцензії: {', '.join(unknowns)}. Перевір вручну перед використанням."
        )

    # Несумісні copyleft версії (GPL-2.0 vs GPL-3.0)
    if "GPL-2.0" in licenses and "GPL-3.0" in licenses:
        blockers.append(
            "GPL-2.0 та GPL-3.0 несумісні між собою (GPL-2.0-only не може лінкуватись з GPL-3.0)."
        )

    return {
        "compatible": len(blockers) == 0,
        "warnings": warnings,
        "blockers": blockers,
    }


def safe_for_commercial_saas(licenses: list[str]) -> tuple[bool, list[str]]:
    """
    Чи безпечно використовувати цей набір ліцензій у платному SaaS-продукті.
    Повертає (safe: bool, reasons: list).
    """
    reasons = []
    for spdx in licenses:
        if not spdx:
            continue
        perms = get_permissions(spdx)
        cat = perms.get("category")
        if cat == "network-copyleft":
            reasons.append(f"{spdx}: AGPL — для SaaS треба відкрити код")
        elif cat == "strong-copyleft":
            reasons.append(f"{spdx}: GPL — деривативний продукт також має бути GPL")
        elif cat == "unknown":
            reasons.append(f"{spdx}: ліцензія невідома, потрібна перевірка")
    return (len(reasons) == 0, reasons)
