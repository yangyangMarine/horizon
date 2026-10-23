"""
transcript_cleaning.py
Normalizes Chinese macroeconomic terminology, standardizes numbers,
and flags uncertain spoken phrases.
"""

import re
from typing import List
from src.macro_expert.models import TranscriptSegment

FINANCIAL_TERM_REPLACEMENTS = {
    "隔夜逆回购": "隔夜逆回购(ON RRP)",
    "逆回购协议": "隔夜逆回购(ON RRP)",
    "TGA账户": "财政部一般账户(TGA)",
    "准备金": "银行存款准备金",
    "加息": "加息",
    "降息": "降息",
    "缩表": "量化紧缩(QT)",
    "扩表": "量化宽松(QE)",
    "基点": "基点(bp)",
}

def clean_transcript_segment(seg: TranscriptSegment) -> TranscriptSegment:
    text = seg.text
    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    # Standardize common financial vocabulary
    for term, norm in FINANCIAL_TERM_REPLACEMENTS.items():
        text = text.replace(term, norm)
        
    seg.text = text
    return seg

def clean_segments(segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
    return [clean_transcript_segment(s) for s in segments]
