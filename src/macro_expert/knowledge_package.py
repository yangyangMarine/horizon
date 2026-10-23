"""
knowledge_package.py
Package loader, schema validator, and database synchronization engine.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger
from src.macro_expert.models import CaseStudy, Claim, Forecast, Framework, SourceRecord

logger = setup_logger("horizon.knowledge_package")

class KnowledgePackageManager:
    def __init__(self, package_dir: str = "./expert_pack", db: Optional[Database] = None):
        self.package_dir = Path(package_dir)
        self.db = db

    def load_manifest(self) -> Dict[str, Any]:
        manifest_file = self.package_dir / "manifest.yaml"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_file}")
        with open(manifest_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_sources(self) -> List[SourceRecord]:
        fpath = self.package_dir / "sources/source_catalog.jsonl"
        records = []
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(SourceRecord(**json.loads(line)))
        return records

    def load_claims(self) -> List[Claim]:
        fpath = self.package_dir / "claims/claims.jsonl"
        records = []
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(Claim(**json.loads(line)))
        return records

    def load_cases(self) -> List[CaseStudy]:
        fpath = self.package_dir / "cases/cases.jsonl"
        records = []
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(CaseStudy(**json.loads(line)))
        return records

    def load_forecasts(self) -> List[Forecast]:
        fpath = self.package_dir / "forecasts/forecasts.jsonl"
        records = []
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(Forecast(**json.loads(line)))
        return records

    def load_frameworks(self) -> List[Framework]:
        frameworks_dir = self.package_dir / "frameworks"
        records = []
        if frameworks_dir.exists():
            for md_file in frameworks_dir.glob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                # Parse title from first line # Title
                lines = content.splitlines()
                title = lines[0].replace("#", "").strip() if lines else md_file.stem
                fw_id = md_file.stem
                topic = md_file.stem
                records.append(
                    Framework(
                        id=f"fw_{fw_id}",
                        title=title,
                        topic=topic,
                        version="1.0.0",
                        status="verified",
                        content_markdown=content
                    )
                )
        return records

    def sync_to_database(self) -> Dict[str, int]:
        """Imports all portable package files into the SQLite database and rebuilds FTS."""
        if not self.db:
            raise ValueError("Database instance required for sync_to_database")

        manifest = self.load_manifest()
        sources = self.load_sources()
        claims = self.load_claims()
        cases = self.load_cases()
        forecasts = self.load_forecasts()
        frameworks = self.load_frameworks()

        with self.db.session() as conn:
            # 1. Sync videos / sources
            for s in sources:
                conn.execute(
                    """
                    INSERT INTO videos(video_id, creator_id, title, video_url, publish_date, duration_seconds, review_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(video_id) DO UPDATE SET
                        title = excluded.title,
                        video_url = excluded.video_url,
                        publish_date = excluded.publish_date,
                        review_status = excluded.review_status;
                    """,
                    (s.video_id, s.creator_id, s.title, s.video_url, s.publish_date, s.duration_seconds, s.review_status)
                )

            # 2. Sync claims
            for c in claims:
                conn.execute(
                    """
                    INSERT INTO claims(claim_id, video_id, topic, subtopic, claim_text, claim_type, mechanism, conditions, indicators, assets_affected, time_horizon, confidence_expression, evidence_text, timestamp_range, review_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(claim_id) DO UPDATE SET
                        claim_text = excluded.claim_text,
                        mechanism = excluded.mechanism,
                        conditions = excluded.conditions,
                        evidence_text = excluded.evidence_text,
                        timestamp_range = excluded.timestamp_range,
                        review_status = excluded.review_status;
                    """,
                    (
                        c.claim_id, c.video_id, c.topic, c.subtopic, c.claim_text, c.claim_type,
                        c.mechanism, c.conditions, c.indicators, json.dumps(c.assets_affected),
                        c.time_horizon, c.confidence_expression, c.evidence_text, c.timestamp_range, c.review_status
                    )
                )

            # 3. Sync cases
            for cs in cases:
                conn.execute(
                    """
                    INSERT INTO cases(case_id, name, topic, era, countries, key_indicators, mechanisms, creator_comparative_take, source_video_id, timestamp, review_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(case_id) DO UPDATE SET
                        mechanisms = excluded.mechanisms,
                        creator_comparative_take = excluded.creator_comparative_take,
                        review_status = excluded.review_status;
                    """,
                    (
                        cs.case_id, cs.name, cs.topic, cs.era, json.dumps(cs.countries),
                        json.dumps(cs.key_indicators), cs.mechanisms, cs.creator_comparative_take,
                        cs.source_video_id, cs.timestamp, cs.review_status
                    )
                )

            # 4. Sync forecasts
            for fc in forecasts:
                conn.execute(
                    """
                    INSERT INTO forecasts(forecast_id, video_id, forecast_date, target_variable, direction, target_value, horizon, conditions, forecast_text, review_status, outcome, outcome_date, outcome_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(forecast_id) DO UPDATE SET
                        outcome = excluded.outcome,
                        outcome_date = excluded.outcome_date,
                        outcome_notes = excluded.outcome_notes;
                    """,
                    (
                        fc.forecast_id, fc.video_id, fc.forecast_date, fc.target_variable,
                        fc.direction, fc.target_value, fc.horizon, fc.conditions,
                        fc.forecast_text, fc.review_status, fc.outcome, fc.outcome_date, fc.outcome_notes
                    )
                )

            # 5. Sync frameworks
            for fw in frameworks:
                conn.execute(
                    """
                    INSERT INTO frameworks(id, title, topic, version, status, content_markdown)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title = excluded.title,
                        content_markdown = excluded.content_markdown,
                        status = excluded.status;
                    """,
                    (fw.id, fw.title, fw.topic, fw.version, fw.status, fw.content_markdown)
                )

            # 6. Record package version
            conn.execute(
                """
                INSERT INTO package_versions(version, manifest_json)
                VALUES (?, ?)
                ON CONFLICT(version) DO UPDATE SET manifest_json = excluded.manifest_json;
                """,
                (manifest.get("package_version", "1.0.0"), json.dumps(manifest))
            )

        # Rebuild full-text index
        indexed_count = self.db.rebuild_fts_index()

        counts = {
            "sources": len(sources),
            "claims": len(claims),
            "cases": len(cases),
            "forecasts": len(forecasts),
            "frameworks": len(frameworks),
            "fts_indexed": indexed_count
        }
        logger.info(f"Knowledge package synchronized: {counts}")
        return counts
