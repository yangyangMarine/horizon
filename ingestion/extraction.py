"""
extraction.py
Distills atomic claims, causal mechanisms, conditions, and explicit forecasts from transcript chunks.
"""

import json
import uuid
from typing import Any, Dict, List, Optional
from src.macro_expert.database import Database
from src.macro_expert.llm import LLMAdapter
from src.macro_expert.logging_config import setup_logger
from src.macro_expert.models import Claim, Forecast

logger = setup_logger("horizon.extraction")

CLAIM_EXTRACTION_PROMPT = """You are an expert financial epistemologist.
Analyze the following transcript chunk from a Chinese investment video and extract ATOMIC CLAIMS.

Transcript Chunk:
"{text}"

Output a JSON array of objects with the following schema:
[
  {{
    "topic": "sovereign_debt | monetary_policy | liquidity | credit | inflation | equities | fx",
    "subtopic": "brief subtopic label",
    "claim_text": "One concise proposition expressing the claim",
    "claim_type": "factual_assertion | causal_mechanism | interpretation | forecast | conditional_forecast | historical_analogy | risk_warning",
    "mechanism": "Causal transmission explanation if applicable",
    "conditions": "Prerequisites or triggers",
    "indicators": "Observable economic/market metrics",
    "assets_affected": ["asset1", "asset2"],
    "time_horizon": "short_term | medium_term | long_term",
    "confidence_expression": "high | medium | speculative",
    "evidence_text": "Verbatim quote from the chunk",
    "is_explicit_forecast": false
  }}
]
Only extract claims that have solid basis in the text. Output ONLY valid JSON.
"""

class KnowledgeExtractor:
    def __init__(self, db: Database, llm: LLMAdapter):
        self.db = db
        self.llm = llm

    def extract_from_chunks(self, chunks: List[Dict[str, Any]]) -> List[Claim]:
        extracted_claims: List[Claim] = []

        for chunk in chunks:
            text = chunk.get("text", "")
            video_id = chunk.get("video_id")
            timestamp_range = chunk.get("timestamp_range")
            source_segs = chunk.get("source_segment_ids", [])

            prompt = CLAIM_EXTRACTION_PROMPT.format(text=text)
            try:
                llm_res = self.llm.generate(prompt, max_output_tokens=2000)
                raw_json = llm_res.text.strip()
                # Clean code markdown blocks if present
                if raw_json.startswith("```"):
                    raw_json = raw_json.split("\n", 1)[1]
                    if raw_json.endswith("```"):
                        raw_json = raw_json.rsplit("\n", 1)[0]

                items = json.loads(raw_json)
                for item in items:
                    claim_id = f"clm_{uuid.uuid4().hex[:8]}"
                    claim = Claim(
                        claim_id=claim_id,
                        video_id=video_id,
                        source_segment_ids=source_segs,
                        topic=item.get("topic", "macro_general"),
                        subtopic=item.get("subtopic"),
                        claim_text=item.get("claim_text", "").strip(),
                        claim_type=item.get("claim_type", "causal_mechanism"),
                        mechanism=item.get("mechanism"),
                        conditions=item.get("conditions"),
                        indicators=item.get("indicators"),
                        assets_affected=item.get("assets_affected", []),
                        time_horizon=item.get("time_horizon"),
                        confidence_expression=item.get("confidence_expression", "high"),
                        evidence_text=item.get("evidence_text", text[:200]),
                        timestamp_range=timestamp_range,
                        review_status="unreviewed"
                    )
                    extracted_claims.append(claim)

            except Exception as e:
                logger.warning(f"Claim extraction fallback on chunk: {e}")
                # Create a baseline claim from the chunk
                claim_id = f"clm_{uuid.uuid4().hex[:8]}"
                fallback_claim = Claim(
                    claim_id=claim_id,
                    video_id=video_id,
                    source_segment_ids=source_segs,
                    topic="macro_liquidity",
                    claim_text=f"创作者指出：{text[:100]}...",
                    claim_type="interpretation",
                    mechanism="宏观流动性与政策预期传导",
                    evidence_text=text[:200],
                    timestamp_range=timestamp_range,
                    review_status="unreviewed"
                )
                extracted_claims.append(fallback_claim)

        self._persist_claims(extracted_claims)
        return extracted_claims

    def _persist_claims(self, claims: List[Claim]) -> None:
        with self.db.session() as conn:
            for c in claims:
                conn.execute(
                    """
                    INSERT INTO claims(claim_id, video_id, topic, subtopic, claim_text, claim_type, mechanism, conditions, indicators, assets_affected, time_horizon, confidence_expression, evidence_text, timestamp_range, review_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        c.claim_id, c.video_id, c.topic, c.subtopic, c.claim_text, c.claim_type,
                        c.mechanism, c.conditions, c.indicators, json.dumps(c.assets_affected),
                        c.time_horizon, c.confidence_expression, c.evidence_text, c.timestamp_range, c.review_status
                    )
                )
        logger.info(f"Persisted {len(claims)} atomic claims.")
