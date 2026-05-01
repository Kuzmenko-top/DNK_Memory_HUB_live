#!/usr/bin/env python3
"""bootstrap_library.py — масовий збір репо по DNK-доменах без AI"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from src.search import search_repos
from src.ranker import rank_repos
from src.storage import save_to_library, get_library_stats
from loguru import logger

DOMAINS = {
    "ai-agents": ["autonomous AI agent framework python", "multi-agent LLM orchestration", "AI agent tools memory python"],
    "telegram-bots": ["telegram bot python aiogram async", "telegram business bot automation"],
    "saas-boilerplate": ["nextjs saas boilerplate stripe auth", "full-stack saas starter typescript nextjs", "nextjs app router subscription auth"],
    "landing-pages": ["landing page builder nextjs react tailwind", "one-page website react animated"],
    "copywriting-ai": ["AI copywriting content generation LLM", "marketing copy generator python openai"],
    "logistics": ["ecommerce order fulfillment automation python", "logistics API integration python"],
    "rag-memory": ["RAG retrieval augmented generation python", "vector database embeddings knowledge base", "langchain llama-index rag pipeline"],
    "web-scraping": ["web scraping python playwright async", "browser automation data extraction"],
    "payments": ["stripe payment integration nextjs python", "subscription billing saas stripe"],
    "analytics": ["analytics dashboard nextjs python", "business intelligence reporting automation"],
}

def bootstrap():
    total = 0
    for domain, queries in DOMAINS.items():
        logger.info(f"\n{'='*40}\n🔍 DOMAIN: {domain.upper()}")
        all_repos, seen = [], set()
        for query in queries:
            repos = search_repos(query, max_results=8, min_stars=30)
            for r in repos:
                key = r.get("full_name", r.get("name", ""))
                if key and key not in seen:
                    seen.add(key)
                    r["domain"] = domain
                    all_repos.append(r)
            time.sleep(1.5)
        ranked = rank_repos(all_repos)
        for r in ranked:
            r["domain"] = domain
            r["source"] = "bootstrap"
        save_to_library(ranked)
        total += len(ranked)
        logger.success(f"✅ {domain}: {len(ranked)} repos")
        time.sleep(2)

    stats = get_library_stats()
    logger.success(f"\n🔱 BOOTSTRAP DONE! Бібліотека: {stats['total']} репо в {len(stats['domains'])} доменах")

if __name__ == "__main__":
    bootstrap()
