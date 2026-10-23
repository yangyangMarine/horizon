from src.macro_expert.citations import build_citation_from_search_result, format_citations_markdown
from src.macro_expert.models import SearchResult

def test_citations_formatting():
    res = SearchResult(
        record_id="clm_001",
        source_type="claim",
        title="期限溢价与发债供给",
        content="美债供给放量推升期限溢价。",
        relevance_score=0.85,
        video_id="vid_macro_2023_09_15",
        publish_date="2023-09-15",
        timestamp_range="02:15 - 03:02",
        metadata={"review_status": "verified", "video_url": "https://www.douyin.com/video/123"}
    )

    cite = build_citation_from_search_result(res)
    assert cite.category == "creator_statement"
    assert cite.video_id == "vid_macro_2023_09_15"
    assert cite.timestamp == "02:15 - 03:02"

    md = format_citations_markdown([cite])
    assert "vid_macro_2023_09_15" in md
    assert "02:15 - 03:02" in md
    assert "期限溢价与发债供给" in md
