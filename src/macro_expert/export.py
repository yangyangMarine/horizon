"""
export.py
Portable export and operational backup/restore routines for Horizon.
"""

import hashlib
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
import yaml
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.export")

def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

class ExportManager:
    def __init__(self, package_dir: str = "./expert_pack", export_dir: str = "./data/exports", db: Optional[Database] = None):
        self.package_dir = Path(package_dir)
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.db = db

    def export_expert_package_zip(self, output_filename: Optional[str] = None) -> Path:
        """Packages the expert knowledge pack into a standalone, verifiable ZIP archive."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        fname = output_filename or f"horizon_expert_pack_{timestamp}.zip"
        zip_path = self.export_dir / fname

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.package_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(self.package_dir)
                    zf.write(full_p, arcname=str(rel_p))

        logger.info(f"Expert package exported to {zip_path}")
        return zip_path

    def create_operational_backup_zip(self, output_filename: Optional[str] = None) -> Path:
        """
        Creates an operational backup including a safe SQLite snapshot and knowledge package.
        Never bundles .env or raw secrets.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        fname = output_filename or f"horizon_backup_operational_{timestamp}.zip"
        zip_path = self.export_dir / fname

        # 1. Safely snapshot SQLite DB using sqlite3 backup API
        temp_db_snapshot = self.export_dir / f"snapshot_{timestamp}.db"
        if self.db and self.db.db_path.exists():
            src_conn = sqlite3.connect(str(self.db.db_path))
            dst_conn = sqlite3.connect(str(temp_db_snapshot))
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add SQLite snapshot
                if temp_db_snapshot.exists():
                    zf.write(temp_db_snapshot, arcname="app.db")

                # Add expert package files
                for root, dirs, files in os.walk(self.package_dir):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(self.package_dir)
                        zf.write(full_p, arcname=f"expert_pack/{rel_p}")
        finally:
            if temp_db_snapshot.exists():
                temp_db_snapshot.unlink()

        logger.info(f"Operational backup completed at {zip_path}")
        return zip_path

    def restore_backup(self, zip_path: Path, target_db_path: Path, target_pack_path: Path) -> Tuple[bool, str]:
        """Restores a backup zip into the target database and expert pack directories."""
        if not zip_path.exists():
            return False, f"Backup file {zip_path} does not exist."

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                namelist = zf.namelist()
                # Check for database
                if "app.db" in namelist:
                    target_db_path.parent.mkdir(parents=True, exist_ok=True)
                    zf.extract("app.db", path=target_db_path.parent)
                    # Rename if needed
                    extracted_db = target_db_path.parent / "app.db"
                    if extracted_db != target_db_path:
                        shutil.move(extracted_db, target_db_path)

                # Extract expert_pack
                for member in namelist:
                    if member.startswith("expert_pack/"):
                        rel = member[len("expert_pack/"):]
                        if rel:
                            target_file = target_pack_path / rel
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(member) as source, open(target_file, "wb") as target:
                                shutil.copyfileobj(source, target)

            logger.info(f"Backup restored successfully from {zip_path}")
            return True, "Restoration complete."
        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            return False, str(e)
