"""
orchestrator.py — DNK Brain Hygiene & Orchestration
Нормалізація метаданих, виправлення посилань та гігієна Markdown файлів.
"""
import os
import re
import yaml
import uuid
from datetime import datetime
from pathlib import Path
from loguru import logger

EXCLUDE_DIRS = [".archive", "node_modules", ".git", ".next", "dist", ".gemini", "scripts", "tmp"]
IGNORE_FILES = [".env", ".env.local", ".DS_Store"]

class BrainOrchestrator:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).absolute()
        self.stats = {"sanitized": 0, "ids_fixed": 0}

    def map_subsystem(self, filepath: str) -> str:
        filepath = str(filepath)
        if "reports" in filepath: return "RESEARCH"
        if "01_DNK_LOGIC" in filepath: return "CORE"
        if "02_DNK_EXECUTION" in filepath: return "EXECUTION"
        if "03_DNK_RESOURCES" in filepath: return "RESOURCES"
        return "GENERAL"

    def sanitize_links(self, content: str) -> str:
        """Видаляє витоки абсолютних шляхів."""
        pattern = r"file:///Users/kuzmenko\.top/[^\s\)]+"
        return re.sub(pattern, "RELATIVE_PATH_LEAK_CLEANED", content)

    def process_md_file(self, path: Path):
        """Нормалізація фронтметтеру та змісту MD файлу."""
        if not path.suffix == ".md":
            return

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Frontmatter check
        fm_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        body = content
        data = {}
        
        if fm_match:
            fm_raw = fm_match.group(1)
            body = content[fm_match.end():]
            try:
                data = yaml.safe_load(fm_raw) or {}
            except:
                data = {}
        
        # 2. Field Normalization
        subsystem = self.map_subsystem(str(path))
        sid = data.get('synapse_id') or data.get('id')
        
        if not sid or sid == "PREFIX_[UNIQUE_ID]":
            name = path.stem.upper()
            sid = f"KNOW_{name}_{uuid.uuid4().hex[:6].upper()}"
            self.stats["ids_fixed"] += 1

        optimized = {
            'synapse_id': sid,
            'title': data.get('title') or path.stem.replace("_", " ").title(),
            'type': data.get('type') or 'research_node',
            'subsystem': subsystem,
            'status': data.get('status') or 'ACTIVE',
            'version': data.get('version') or '1.2.0',
            'last_update': datetime.now().strftime("%Y-%m-%d")
        }

        # 3. Reconstruct
        new_fm = "---\n"
        for k, v in optimized.items():
            new_fm += f"{k}: {v}\n"
        new_fm += "---\n"

        new_content = self.sanitize_links(new_fm + body)
        
        if new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            self.stats["sanitized"] += 1

    def run_hygiene(self, target_folders: list[str] = ["data/reports"]):
        """Запуск процесу очищення."""
        logger.info(f"🧬 Starting Brain Hygiene in {target_folders}...")
        for folder in target_folders:
            folder_path = self.base_dir / folder
            if not folder_path.exists():
                continue
            
            for root, dirs, files in os.walk(folder_path):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
                for file in files:
                    if file.endswith(".md"):
                        self.process_md_file(Path(root) / file)
        
        logger.success(f"🏁 Finished. Sanitized: {self.stats['sanitized']} | IDs Fixed: {self.stats['ids_fixed']}")
        return self.stats
