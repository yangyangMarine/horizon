#!/usr/bin/env python3
"""
backup.py
Creates an operational backup of SQLite database and expert knowledge assets.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.macro_expert.config import load_config
from src.macro_expert.database import Database
from src.macro_expert.export import ExportManager

def main():
    config = load_config()
    db = Database(config.storage.database_path)
    export_mgr = ExportManager(
        package_dir=config.knowledge.package_path,
        export_dir=config.knowledge.export_path,
        db=db
    )
    backup_zip = export_mgr.create_operational_backup_zip()
    print(f"[OK] Operational backup created successfully at: {backup_zip}")

if __name__ == "__main__":
    main()
