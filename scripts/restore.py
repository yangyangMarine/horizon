#!/usr/bin/env python3
"""
restore.py
Restores an operational backup from a ZIP archive.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.macro_expert.config import load_config
from src.macro_expert.export import ExportManager

def main():
    parser = argparse.ArgumentParser(description="Restore Horizon backup archive")
    parser.add_argument("backup_file", type=str, help="Path to backup ZIP file")
    args = parser.parse_args()

    config = load_config()
    export_mgr = ExportManager(
        package_dir=config.knowledge.package_path,
        export_dir=config.knowledge.export_path
    )
    success, msg = export_mgr.restore_backup(
        zip_path=Path(args.backup_file),
        target_db_path=Path(config.storage.database_path),
        target_pack_path=Path(config.knowledge.package_path)
    )
    if success:
        print(f"[OK] Restore completed: {msg}")
    else:
        print(f"[ERROR] Restore failed: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
