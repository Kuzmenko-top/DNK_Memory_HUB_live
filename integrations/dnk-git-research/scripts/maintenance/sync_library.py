import os
import re
import json
from pathlib import Path
from datetime import datetime
import yaml

def sync():
    root = Path.cwd()
    audit_dir = root / "data" / "DNK_Repo_AUDIT"
    library_path = root / "data" / "library.json"
    
    if not audit_dir.exists():
        print(f"❌ Directory not found: {audit_dir}")
        return

    repos = {}
    md_files = list(audit_dir.glob("*.md"))
    print(f"🔍 Found {len(md_files)} audit files. Processing...")

    for md_file in md_files:
        if md_file.name == "AUDIT_SUMMARY_TABLE.md":
            continue
            
        try:
            content = md_file.read_text(encoding='utf-8')
            
            # Extract frontmatter
            frontmatter = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                    except:
                        pass
            
            # Extract repo name from header
            repo_match = re.search(r"## 🚀 АНАЛІЗ РЕПОЗИТОРІЮ: ([\w\-/]+)", content)
            full_name = repo_match.group(1) if repo_match else md_file.stem.replace("_", "/")
            
            # Extract summary
            summary_match = re.search(r"### 1\. СУТЬ ПРОЄКТУ:\n(.*?)\n", content, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ""
            
            # Extract license
            license_match = re.search(r"### 2\. ЛІЦЕНЗІЯ:\n.*?([\w\.\-]+)", content, re.DOTALL)
            license_str = license_match.group(1) if license_match else "unknown"
            
            # Simple scoring estimation (if not present)
            score = 7.0 # Default for legacy
            if "MIT" in license_str or "Apache" in license_str:
                score += 1.0
            
            repos[full_name] = {
                "full_name": full_name,
                "name": full_name.split("/")[-1],
                "url": f"https://github.com/{full_name}",
                "summary_ua": summary[:200],
                "license": license_str,
                "dnk_total_score": score,
                "synapse_id": frontmatter.get("synapse_id", ""),
                "domain": "migrated",
                "saved_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"⚠️ Error processing {md_file.name}: {e}")

    library_data = {
        "repos": repos,
        "meta": {
            "total": len(repos),
            "last_updated": datetime.utcnow().isoformat()
        }
    }
    
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(library_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Library synced! {len(repos)} repositories indexed into {library_path}")

if __name__ == "__main__":
    sync()
