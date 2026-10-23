#!/usr/bin/env python3
"""
extract_knowledge.py
CLI tool to distill claims and mechanisms from transcribed segments.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.chunking import TranscriptChunker
from ingestion.extraction import KnowledgeExtractor
from ingestion.transcript_cleaning import clean_segments
from src.macro_expert.config import load_config
from src.macro_expert.database import Database
from src.macro_expert.llm import get_llm_adapter
from src.macro_expert.models import TranscriptSegment

def main():
    parser = argparse.ArgumentParser(description="Extract knowledge from transcribed videos")
    parser.add_argument("--video_id", type=str, help="Specific video_id")
    args = parser.parse_args()

    config = load_config()
    db = Database(config.storage.database_path)
    llm = get_llm_adapter(config)
    chunker = TranscriptChunker()
    extractor = KnowledgeExtractor(db, llm)

    with db.session() as conn:
        if args.video_id:
            cur = conn.execute("SELECT * FROM transcript_segments WHERE video_id = ? ORDER BY start_seconds ASC;", (args.video_id,))
        else:
            cur = conn.execute("SELECT * FROM transcript_segments ORDER BY video_id, start_seconds ASC;")
        rows = cur.fetchall()

    if not rows:
        print("No transcript segments found to process.")
        return

    # Group by video
    video_map = {}
    for r in rows:
        vid = r["video_id"]
        video_map.setdefault(vid, []).append(
            TranscriptSegment(
                segment_id=r["segment_id"],
                video_id=r["video_id"],
                start_seconds=r["start_seconds"],
                end_seconds=r["end_seconds"],
                text=r["text"],
                confidence=r["confidence"],
                review_status=r["review_status"]
            )
        )

    for vid, segs in video_map.items():
        cleaned = clean_segments(segs)
        chunks = chunker.chunk_segments(cleaned)
        claims = extractor.extract_from_chunks(chunks)
        print(f"[OK] Video {vid}: Extracted {len(claims)} atomic claims from {len(chunks)} chunks.")

    db.rebuild_fts_index()
    print("[OK] Search index updated.")

if __name__ == "__main__":
    main()
