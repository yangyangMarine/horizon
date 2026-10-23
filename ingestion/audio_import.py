"""
audio_import.py
Ingests authorized media files (MP4, MP3, WAV, M4A), validates formats,
and computes checksums to prevent duplicate transcription.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.audio_import")

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".aac", ".ogg", ".flac"}

def compute_file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

class AudioImporter:
    def __init__(self, db: Database, audio_storage_dir: str = "./data/audio"):
        self.db = db
        self.storage_dir = Path(audio_storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def import_media_file(self, source_path: Path, video_id: str) -> Tuple[Path, str]:
        ext = source_path.suffix.lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: {ALLOWED_AUDIO_EXTENSIONS}")

        checksum = compute_file_hash(source_path)
        dest_filename = f"{video_id}_{checksum[:8]}{ext}"
        dest_path = self.storage_dir / dest_filename

        if not dest_path.exists():
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied audio to {dest_path}")
        else:
            logger.info(f"Media file already exists in storage: {dest_path}")

        with self.db.session() as conn:
            conn.execute(
                """
                UPDATE videos 
                SET audio_path = ?, checksum = ?, ingestion_status = 'audio_imported', updated_at = CURRENT_TIMESTAMP
                WHERE video_id = ?;
                """,
                (str(dest_path), checksum, video_id)
            )

        return dest_path, checksum
