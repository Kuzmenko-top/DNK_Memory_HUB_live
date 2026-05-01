#!/usr/bin/env python3
"""
search_knowledge.py — семантичний пошук в Qdrant github_repos.
Використання: python3 search_knowledge.py "запит" [--top 5]
"""
from __future__ import annotations
import sys
import os
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = "github_repos"
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "dnk-ai-agent")
SA_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path(__file__).parent.parent.parent / "memory" / "ingestion" / "service-account.json"),  # DNK_HUB/memory/ingestion
)


def get_token() -> str | None:
    if not os.path.exists(SA_PATH):
        print(f"[!] Service account not found: {SA_PATH}")
        return None
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        creds = service_account.Credentials.from_service_account_file(
            SA_PATH, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except Exception as e:
        print(f"[!] Auth error: {e}")
        return None


def embed(text: str, token: str) -> list[float] | None:
    url = (
        f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/us-central1/publishers/google/models/text-embedding-004:predict"
    )
    payload = json.dumps({"instances": [{"task_type": "RETRIEVAL_QUERY", "content": text[:8000]}]}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["predictions"][0]["embeddings"]["values"]
    except Exception as e:
        print(f"[!] Embed error: {e}")
        return None


def search(query: str, top_k: int = 5) -> list[dict]:
    token = get_token()
    if not token:
        return []

    vec = embed(query, token)
    if not vec:
        return []

    payload = json.dumps({"vector": vec, "limit": top_k, "with_payload": True}).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        data=payload, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return [{"score": hit["score"], **hit["payload"]} for hit in data.get("result", [])]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "Not found" in body:
            print(f"[!] Колекція '{COLLECTION}' порожня — спочатку запусти batch_analyze.py")
        else:
            print(f"[!] Qdrant error {e.code}: {body[:200]}")
        return []
    except Exception as e:
        print(f"[!] Search error: {e}")
        return []


def main():
    args = sys.argv[1:]
    if not args:
        print("Використання: python3 search_knowledge.py \"запит\" [--top N]")
        sys.exit(1)

    top_k = 5
    if "--top" in args:
        idx = args.index("--top")
        top_k = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    query = " ".join(args)
    print(f"\n🔍 Пошук: \"{query}\" (top-{top_k})\n")

    results = search(query, top_k=top_k)
    if not results:
        print("Нічого не знайдено.")
        return

    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        name = r.get("full_name", "?")
        what = r.get("what_it_does", r.get("description", "—"))
        how = r.get("how_to_use", "—")
        key_files = r.get("reverse_engineering", {}).get("key_files", [])
        difficulty = r.get("integration_difficulty", "—")
        stars = r.get("stars", 0)

        print(f"{'─'*60}")
        print(f"#{i} [{score:.3f}] ⭐{stars:,}  {name}")
        print(f"   Що: {what[:120]}")
        print(f"   Як використати: {how[:100]}")
        if key_files:
            print(f"   Ключові файли: {', '.join(key_files[:3])}")
        print(f"   Складність: {difficulty}")

    print(f"\n{'─'*60}")
    print(f"Знайдено: {len(results)} репо")


if __name__ == "__main__":
    main()
