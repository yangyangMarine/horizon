#!/usr/bin/env python3
"""
build_index.py
Synchronizes expert package and rebuilds SQLite FTS5 index.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.macro_expert.config import load_config
from src.macro_expert.database import Database
from src.macro_expert.knowledge_package import KnowledgePackageManager

def main():
    config = load_config()
    db = Database(config.storage.database_path)
    pkg_mgr = KnowledgePackageManager(config.knowledge.package_path, db)
    print("Synchronizing expert knowledge package to database...")
    counts = pkg_mgr.sync_to_database()
    print(f"[OK] Synchronization complete: {counts}")

if __name__ == "__main__":
    main()
