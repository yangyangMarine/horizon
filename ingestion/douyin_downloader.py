"""
douyin_downloader.py
Safely downloads or extracts audio from Douyin video URLs using yt-dlp,
with browser cookie support and fallback handling.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.douyin_downloader")

class DouyinDownloader:
    def __init__(self, download_dir: str = "./data/audio"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_audio_from_url(
        self,
        video_url: str,
        video_id: str,
        browser_cookies: Optional[str] = "edge"  # chrome, edge, firefox, or None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Extracts the audio track from a Douyin video page using yt-dlp.
        Returns (audio_path, error_message).
        """
        output_template = str(self.download_dir / f"{video_id}.%(ext)s")
        expected_mp3 = self.download_dir / f"{video_id}.mp3"
        expected_m4a = self.download_dir / f"{video_id}.m4a"

        # Check if already downloaded
        if expected_mp3.exists():
            return expected_mp3, None
        if expected_m4a.exists():
            return expected_m4a, None

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--output", output_template,
            "--no-playlist",
            "--quiet",
            "--no-warnings"
        ]

        if browser_cookies:
            cmd.extend(["--cookies-from-browser", browser_cookies])

        cmd.append(video_url)

        try:
            logger.info(f"Downloading audio for {video_id} from {video_url}...")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                # Find output file
                for ext in [".mp3", ".m4a", ".webm", ".opus"]:
                    candidate = self.download_dir / f"{video_id}{ext}"
                    if candidate.exists():
                        logger.info(f"Downloaded audio to: {candidate}")
                        return candidate, None
                return None, "Download finished but target file not found."
            else:
                err = res.stderr.strip() or res.stdout.strip()
                logger.warning(f"yt-dlp download failed for {video_url}: {err}")
                return None, err
        except subprocess.TimeoutExpired:
            return None, "Download timed out (120s)."
        except Exception as e:
            return None, str(e)
