"""
chunking.py
Chunks transcript segments into semantically coherent windows preserving time ranges.
"""

from typing import List
from src.macro_expert.models import TranscriptSegment

class TranscriptChunker:
    def __init__(self, target_tokens: int = 300, max_tokens: int = 500, overlap_segments: int = 1):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_segments = overlap_segments

    def chunk_segments(self, segments: List[TranscriptSegment]) -> List[dict]:
        if not segments:
            return []

        chunks = []
        i = 0
        n = len(segments)

        while i < n:
            curr_chunk_segs = []
            curr_len = 0
            j = i
            while j < n and curr_len < self.target_tokens:
                curr_chunk_segs.append(segments[j])
                curr_len += len(segments[j].text)
                j += 1

            start_t = curr_chunk_segs[0].start_seconds
            end_t = curr_chunk_segs[-1].end_seconds
            combined_text = " ".join([s.text for s in curr_chunk_segs])
            seg_ids = [s.segment_id for s in curr_chunk_segs]

            chunks.append({
                "video_id": segments[0].video_id,
                "start_seconds": start_t,
                "end_seconds": end_t,
                "timestamp_range": f"{int(start_t // 60):02d}:{int(start_t % 60):02d} - {int(end_t // 60):02d}:{int(end_t % 60):02d}",
                "text": combined_text,
                "source_segment_ids": seg_ids
            })

            # Advance with overlap
            step = max(1, len(curr_chunk_segs) - self.overlap_segments)
            i += step

        return chunks
