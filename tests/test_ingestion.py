import tempfile
from pathlib import Path
from ingestion.chunking import TranscriptChunker
from ingestion.metadata_import import MetadataImporter
from ingestion.pipeline import IngestPipeline
from ingestion.transcript_cleaning import clean_segments
from src.macro_expert.database import Database
from src.macro_expert.llm import MockLLMAdapter
from src.macro_expert.models import TranscriptSegment

def test_metadata_importer():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test_ing.db"))
        importer = MetadataImporter(db)

        url = "https://www.douyin.com/video/7220000000000000099"
        vid_id, is_new = importer.register_video(url, "测试新宏观视频")
        assert is_new is True
        assert "7220000000000000099" in vid_id

        # Duplicate detection
        vid_id2, is_new2 = importer.register_video(url, "测试新宏观视频")
        assert is_new2 is False
        assert vid_id2 == vid_id

def test_chunking_and_cleaning():
    segs = [
        TranscriptSegment(segment_id="s1", video_id="v1", start_seconds=0.0, end_seconds=10.0, text="我们看到隔夜逆回购大幅减少。"),
        TranscriptSegment(segment_id="s2", video_id="v1", start_seconds=10.0, end_seconds=20.0, text="同时财政部TGA账户开始放量扩张。")
    ]
    cleaned = clean_segments(segs)
    assert "隔夜逆回购(ON RRP)" in cleaned[0].text
    assert "财政部一般账户(TGA)" in cleaned[1].text

    chunker = TranscriptChunker(target_tokens=50)
    chunks = chunker.chunk_segments(cleaned)
    assert len(chunks) >= 1
    assert "00:00 - 00:20" in chunks[0]["timestamp_range"]

def test_ingest_pipeline_end_to_end():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test_pipe.db"))
        llm = MockLLMAdapter(
            canned_response='[{"topic": "sovereign_debt", "claim_text": "国债供给超预期推升长端利率", "claim_type": "causal_mechanism", "confidence_expression": "high"}]'
        )
        pipeline = IngestPipeline(db, llm, package_dir="expert_pack")

        sample_transcript = (
            "今天我们来复盘最新的美债发债计划。\n"
            "财政部计划大幅增加中长期国债发行，这一举措将显著推升期限溢价。\n"
            "当一级交易商吸收不了这么庞大的供给时，收益率只能往上走。"
        )

        res = pipeline.process_new_video(
            url="https://www.douyin.com/video/7330000000000000001",
            title="最新美债发债计划与收益率冲击",
            transcript_text=sample_transcript,
            publish_date="2026-03-01"
        )

        assert res["status"] == "success"
        assert res["segments_count"] > 0
        assert res["claims_count"] > 0

        # Verify it became searchable in SQLite FTS with 3+ character trigram
        with db.session() as conn:
            cur = conn.execute("SELECT COUNT(*) as cnt FROM knowledge_fts WHERE knowledge_fts MATCH '发债计划';")
            assert cur.fetchone()["cnt"] > 0
