#!/usr/bin/env python3
"""
export_package.py
Packages the expert knowledge pack into a verifiable ZIP archive.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.macro_expert.config import load_config
from src.macro_expert.export import ExportManager

def main():
    config = load_config()
    export_mgr = ExportManager(
        package_dir=config.knowledge.package_path,
        export_dir=config.knowledge.export_path
    )
    zip_path = export_mgr.export_expert_package_zip()
    print(f"[OK] Expert package exported successfully to: {zip_path}")

if __name__ == "__main__":
    main()
