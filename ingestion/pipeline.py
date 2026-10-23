"""
pipeline.py
End-to-end staged video ingestion and knowledge distillation pipeline.
Allows 1-click or automated update when new videos are published.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from ingestion.audio_import import AudioImporter
from ingestion.chunking import TranscriptChunker
from ingestion.extraction import KnowledgeExtractor
from ingestion.framework_builder import FrameworkBuilder
from ingestion.metadata_import import MetadataImporter
from ingestion.transcript_cleaning import clean_segments
from ingestion.transcription import Transcriber
from src.macro_expert.database import Database
from src.macro_expert.knowledge_package import KnowledgePackageManager
from src.macro_expert.llm import LLMAdapter
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.ingest_pipeline")

class IngestPipeline:
    def __init__(self, db: Database, llm: LLMAdapter, package_dir: str = "./expert_pack"):
        self.db = db
        self.llm = llm
        self.package_dir = Path(package_dir)
        self.meta_importer = MetadataImporter(db)
        self.audio_importer = AudioImporter(db)
        self.transcriber = Transcriber(db, llm)
        self.chunker = TranscriptChunker()
        self.extractor = KnowledgeExtractor(db, llm)
        self.framework_builder = FrameworkBuilder(db, llm, package_dir)
        self.pkg_manager = KnowledgePackageManager(package_dir, db)

    def process_new_video(
        self,
        url: str,
        title: str,
        media_path: Optional[Path] = None,
        transcript_text: Optional[str] = None,
        publish_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the staged pipeline:
        1. Register metadata
        2. Audio import / validation (if media provided)
        3. Transcription (multimodal or manual text)
        4. Cleaning & normalization
        5. Semantic chunking
        6. Atomic claims & causal mechanisms extraction
        7. Rebuild search index
        """
        logger.info(f"Starting pipeline for video: '{title}' ({url})")
        # Step 1: Metadata
        video_id, is_new = self.meta_importer.register_video(
            url=url,
            title=title,
            publish_date=publish_date
        )

        # Step 2 & 3: Audio or Transcript
        segments = []
        if media_path and media_path.exists():
            dest_audio, checksum = self.audio_importer.import_media_file(media_path, video_id)
            segments = self.transcriber.transcribe_audio_file(video_id, dest_audio)
        elif transcript_text:
            segments = self.transcriber.import_manual_transcript(video_id, transcript_text)
        else:
            # Registering without media yet
            return {
                "video_id": video_id,
                "status": "metadata_only",
                "message": "视频元数据已收录，等待上传音频或输入文本进行转录。"
            }

        # Step 4: Cleaning
        cleaned_segments = clean_segments(segments)

        # Step 5: Chunking
        chunks = self.chunker.chunk_segments(cleaned_segments)

        # Step 6: Claim & Mechanism Extraction
        claims = self.extractor.extract_from_chunks(chunks)

        # Step 7: Update search index
        indexed_count = self.db.rebuild_fts_index()

        with self.db.session() as conn:
            conn.execute(
                """
                UPDATE videos 
                SET extraction_status = 'completed', ingestion_status = 'fully_indexed', updated_at = CURRENT_TIMESTAMP
                WHERE video_id = ?;
                """,
                (video_id,)
            )

        logger.info(f"Pipeline completed for {video_id}: {len(segments)} segments, {len(claims)} claims, {indexed_count} indexed.")
        return {
            "video_id": video_id,
            "status": "success",
            "segments_count": len(segments),
            "claims_count": len(claims),
            "fts_indexed": indexed_count,
            "message": f"视频《{title}》已成功收录并提炼，检索索引已即时更新！"
        }
