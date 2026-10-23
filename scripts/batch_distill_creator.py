#!/usr/bin/env python3
"""
batch_distill_creator.py
Full-corpus distillation orchestrator for a creator's video collection.
Features sequential processing, checkpointing, auto-resume, and index sync.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.douyin_downloader import DouyinDownloader
from ingestion.pipeline import IngestPipeline
from src.macro_expert.config import load_config
from src.macro_expert.database import Database
from src.macro_expert.llm import get_llm_adapter
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.batch_distill")

def main():
    parser = argparse.ArgumentParser(description="抖音博主全量视频知识蒸馏批处理执行器")
    parser.add_argument("--playlist", type=str, required=True, help="视频清单 JSON 文件路径 (如 douyin_videos.json)")
    parser.add_argument("--browser", type=str, default="edge", help="提取 Cookies 浏览器 (edge, chrome)")
    parser.add_argument("--limit", type=int, default=0, help="最多处理视频数量 (0 为处理全部)")
    parser.add_argument("--delay", type=float, default=2.0, help="每个视频之间的间隔秒数 (防高频请求)")

    args = parser.parse_args()
    playlist_file = Path(args.playlist)
    if not playlist_file.exists():
        print(f"[ERROR] 找不到视频清单文件: {playlist_file}")
        sys.exit(1)

    with open(playlist_file, "r", encoding="utf-8") as f:
        videos = json.load(f)

    if not isinstance(videos, list):
        print("[ERROR] JSON 文件格式应为数组: [{'url': '...', 'title': '...'}, ...]")
        sys.exit(1)

    config = load_config()
    db = Database(config.storage.database_path)
    llm = get_llm_adapter(config)
    pipeline = IngestPipeline(db, llm, config.knowledge.package_path)
    downloader = DouyinDownloader(config.knowledge.audio_path)

    total_count = len(videos)
    if args.limit > 0:
        videos = videos[:args.limit]

    print("=" * 70)
    print(f"🧭 Horizon 创作者全量视频蒸馏流水线启动")
    print(f"待处理视频总数: {len(videos)} 条 (源文件共 {total_count} 条)")
    print(f"音频缓存目录: {config.knowledge.audio_path}")
    print("=" * 70)

    success_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, item in enumerate(videos, start=1):
        url = item.get("url")
        title = item.get("title") or f"视频_{idx}"
        pub_date = item.get("publish_date")

        if not url:
            continue

        print(f"\n[{idx}/{len(videos)}] 处理视频: 《{title}》")
        print(f"URL: {url}")

        # Check if already fully processed in SQLite
        with db.session() as conn:
            cur = conn.execute("SELECT video_id, ingestion_status FROM videos WHERE video_url = ?;", (url,))
            existing = cur.fetchone()
            if existing and existing["ingestion_status"] == "fully_indexed":
                print(f"⏭️ 该视频此前已完成知识蒸馏与索引 (video_id: {existing['video_id']})，自动跳过。")
                skipped_count += 1
                continue

        # 1. Download or locate audio
        # Generate video_id
        from ingestion.metadata_import import extract_douyin_video_id
        raw_id = extract_douyin_video_id(url) or f"v_{idx}"
        vid_id = f"vid_{raw_id}"

        audio_path, err = downloader.download_audio_from_url(
            video_url=url,
            video_id=vid_id,
            browser_cookies=args.browser
        )

        if not audio_path or not audio_path.exists():
            print(f"⚠️ 音频下载未成功 ({err})。尝试使用备用文本或登记元数据。")
            res = pipeline.process_new_video(
                url=url,
                title=title,
                media_path=None,
                transcript_text=item.get("transcript"),
                publish_date=pub_date
            )
            failed_count += 1
            continue

        # 2. Run ingestion pipeline
        try:
            res = pipeline.process_new_video(
                url=url,
                title=title,
                media_path=audio_path,
                transcript_text=item.get("transcript"),
                publish_date=pub_date
            )
            print(f"✅ {res['message']} (主张数: {res.get('claims_count', 0)})")
            success_count += 1
        except Exception as e:
            print(f"❌ 蒸馏处理发生异常: {e}")
            failed_count += 1

        if args.delay > 0 and idx < len(videos):
            time.sleep(args.delay)

    print("\n" + "=" * 70)
    print("🎉 批处理任务执行完毕！")
    print(f"成功蒸馏: {success_count} 个")
    print(f"此前已收录跳过: {skipped_count} 个")
    print(f"失败/待重试: {failed_count} 个")
    print("所有提炼的宏观框架与主张已即时同步至本地专家知识库。")
    print("=" * 70)

if __name__ == "__main__":
    main()
