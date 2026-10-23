"""
metadata_import.py
Imports and normalizes Douyin video URLs, metadata, and handles duplicate detection.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.metadata_import")

DOUYIN_VIDEO_ID_PATTERN = re.compile(r"/video/(\d+)")

def extract_douyin_video_id(url: str) -> Optional[str]:
    match = DOUYIN_VIDEO_ID_PATTERN.search(url)
    if match:
        return match.group(1)
    # Hash fallback if custom or shortened URL
    clean = url.strip()
    if clean:
        return f"url_{hashlib.md5(clean.encode('utf-8')).hexdigest()[:12]}"
    return None

class MetadataImporter:
    def __init__(self, db: Database):
        self.db = db

    def register_video(
        self,
        url: str,
        title: str,
        publish_date: Optional[str] = None,
        duration_seconds: Optional[int] = 0,
        creator_id: str = "douyin_macro_investor"
    ) -> Tuple[str, bool]:
        """
        Registers a video record in SQLite.
        Returns (video_id, is_new).
        """
        raw_vid_id = extract_douyin_video_id(url) or f"vid_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        video_id = f"vid_{raw_vid_id}"

        with self.db.session() as conn:
            cur = conn.execute("SELECT video_id, ingestion_status FROM videos WHERE video_id = ?;", (video_id,))
            existing = cur.fetchone()
            if existing:
                logger.info(f"Video {video_id} already exists with status: {existing['ingestion_status']}")
                return video_id, False

            conn.execute(
                """
                INSERT INTO videos(video_id, creator_id, title, video_url, publish_date, duration_seconds, ingestion_status)
                VALUES (?, ?, ?, ?, ?, ?, 'metadata_registered');
                """,
                (video_id, creator_id, title, url, publish_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"), duration_seconds)
            )
            logger.info(f"Registered new video record: {video_id} - '{title}'")
            return video_id, True
