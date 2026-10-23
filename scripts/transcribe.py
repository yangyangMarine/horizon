#!/usr/bin/env python3
"""
transcribe.py
CLI tool to transcribe pending audio files in the video inventory.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.transcription import Transcriber
from src.macro_expert.config import load_config
from src.macro_expert.database import Database
from src.macro_expert.llm import get_llm_adapter

def main():
    parser = argparse.ArgumentParser(description="Transcribe pending video audio")
    parser.add_argument("--video_id", type=str, help="Specific video_id to transcribe")
    args = parser.parse_args()

    config = load_config()
    db = Database(config.storage.database_path)
    llm = get_llm_adapter(config)
    transcriber = Transcriber(db, llm)

    with db.session() as conn:
        if args.video_id:
            cur = conn.execute("SELECT video_id, audio_path FROM videos WHERE video_id = ?;", (args.video_id,))
        else:
            cur = conn.execute("SELECT video_id, audio_path FROM videos WHERE transcription_status = 'pending' AND audio_path IS NOT NULL;")
        rows = cur.fetchall()

    if not rows:
        print("No pending audio files found to transcribe.")
        return

    print(f"Transcribing {len(rows)} video audio files...")
    for r in rows:
        vid = r["video_id"]
        apath = Path(r["audio_path"])
        if apath.exists():
            segs = transcriber.transcribe_audio_file(vid, apath)
            print(f"[OK] Video {vid}: Transcribed {len(segs)} segments.")
        else:
            print(f"[WARNING] Audio path not found for {vid}: {apath}")

if __name__ == "__main__":
    main()
