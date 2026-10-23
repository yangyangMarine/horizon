"""
citations.py
Citation modeling, verification tracking, and Markdown/HTML formatting.
"""

from typing import List, Optional
from src.macro_expert.models import AttributedCitation, SearchResult

CATEGORY_LABELS = {
    "creator_statement": "创作者原话",
    "creator_framework": "创作者框架",
    "ai_extrapolation": "AI 推演与延伸",
    "external_fact": "外部客观事实",
}

def build_citation_from_search_result(result: SearchResult) -> AttributedCitation:
    meta = result.metadata or {}
    category = "creator_framework" if result.source_type == "framework" else "creator_statement"

    return AttributedCitation(
        citation_id=f"cite_{result.record_id}",
        category=category,
        title=result.title or meta.get("title", "未命名资料"),
        video_id=result.video_id or meta.get("video_id"),
        video_url=meta.get("video_url"),
        publish_date=result.publish_date or meta.get("publish_date"),
        timestamp=result.timestamp_range or meta.get("timestamp_range"),
        verbatim_quote=result.content[:240] + ("..." if len(result.content) > 240 else ""),
        verification_status=meta.get("review_status", "verified")
    )

def format_citations_markdown(citations: List[AttributedCitation]) -> str:
    if not citations:
        return ""

    lines = ["\n\n### 📚 溯源依据与证据链 (Traceable Sources & Evidence)\n"]
    for idx, c in enumerate(citations, start=1):
        cat_label = CATEGORY_LABELS.get(c.category, c.category)
        
        # Build metadata tags
        tags = [f"**[{cat_label}]**"]
        if c.publish_date:
            tags.append(f"📅 {c.publish_date}")
        if c.timestamp:
            tags.append(f"⏱️ {c.timestamp}")
        elif c.video_id:
            tags.append("⏱️ 时间戳未标注")
            
        header = f"{idx}. {' · '.join(tags)}: **{c.title}**"
        lines.append(header)
        
        if c.video_id:
            url_part = f" ([观看视频]({c.video_url}))" if c.video_url else ""
            lines.append(f"   - 视频编号: `{c.video_id}`{url_part} · 审核状态: `{c.verification_status}`")
        if c.verbatim_quote:
            clean_quote = c.verbatim_quote.strip().replace("\n", " ")
            lines.append(f"   - 支撑引文: > *\"{clean_quote}\"*")
        lines.append("")

    return "\n".join(lines)
