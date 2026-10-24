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

def format_citations_markdown(citations: list) -> str:
    if not citations:
        return ""

    lines = ["\n\n### 📚 溯源依据与证据链 (Traceable Sources & Evidence)\n"]
    for idx, c in enumerate(citations, start=1):
        if isinstance(c, dict):
            category = c.get("category", "creator_statement")
            title = c.get("title", "未命名资料")
            publish_date = c.get("publish_date")
            timestamp = c.get("timestamp")
            video_id = c.get("video_id")
            video_url = c.get("video_url")
            verification_status = c.get("verification_status", "verified")
            verbatim_quote = c.get("verbatim_quote", "")
        else:
            category = getattr(c, "category", "creator_statement")
            title = getattr(c, "title", "未命名资料")
            publish_date = getattr(c, "publish_date", None)
            timestamp = getattr(c, "timestamp", None)
            video_id = getattr(c, "video_id", None)
            video_url = getattr(c, "video_url", None)
            verification_status = getattr(c, "verification_status", "verified")
            verbatim_quote = getattr(c, "verbatim_quote", "")

        cat_label = CATEGORY_LABELS.get(category, category)
        
        # Build metadata tags
        tags = [f"**[{cat_label}]**"]
        if publish_date:
            tags.append(f"📅 {publish_date}")
        if timestamp:
            tags.append(f"⏱️ {timestamp}")
        elif video_id:
            tags.append("⏱️ 时间戳未标注")
            
        header = f"{idx}. {' · '.join(tags)}: **{title}**"
        lines.append(header)
        
        if video_id:
            url_part = f" ([观看视频]({video_url}))" if video_url else ""
            lines.append(f"   - 视频编号: `{video_id}`{url_part} · 审核状态: `{verification_status}`")
        if verbatim_quote:
            clean_quote = verbatim_quote.strip().replace("\n", " ")
            lines.append(f"   - 支撑引文: > *\"{clean_quote}\"*")
        lines.append("")

    return "\n".join(lines)
