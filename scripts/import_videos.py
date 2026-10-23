#!/usr/bin/env python3
"""
import_videos.py
CLI tool to easily import new Douyin videos into the Horizon knowledge base.
Supports single URL processing or batch file import.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.pipeline import IngestPipeline
from src.macro_expert.config import load_config
from src.macro_expert.database import Database
from src.macro_expert.llm import get_llm_adapter

def main():
    parser = argparse.ArgumentParser(description="Horizon Video Ingestion CLI")
    parser.add_argument("--url", type=str, help="Douyin video URL")
    parser.add_argument("--title", type=str, help="Video title")
    parser.add_argument("--audio", type=str, help="Path to media file (mp4, mp3, m4a)")
    parser.add_argument("--transcript", type=str, help="Path to transcript text file")
    parser.add_argument("--batch", type=str, help="JSON file containing array of video items to import")

    args = parser.parse_args()
    config = load_config()
    db = Database(config.storage.database_path)
    llm = get_llm_adapter(config)
    pipeline = IngestPipeline(db, llm, config.knowledge.package_path)

    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"[ERROR] Batch file {batch_path} not found.")
            sys.exit(1)
        with open(batch_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        print(f"Starting batch import of {len(items)} videos...")
        for item in items:
            media = Path(item["audio"]) if item.get("audio") else None
            trans = Path(item["transcript"]).read_text(encoding="utf-8") if item.get("transcript") else None
            res = pipeline.process_new_video(
                url=item["url"],
                title=item["title"],
                media_path=media,
                transcript_text=trans,
                publish_date=item.get("publish_date")
            )
            print(f"-> {res['message']}")
    elif args.url and args.title:
        media = Path(args.audio) if args.audio else None
        trans = Path(args.transcript).read_text(encoding="utf-8") if args.transcript else None
        res = pipeline.process_new_video(
            url=args.url,
            title=args.title,
            media_path=media,
            transcript_text=trans
        )
        print(f"[OK] {res['message']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
