"""
models.py
Domain models and schema definitions for the Horizon expert platform.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SourceRecord(BaseModel):
    video_id: str
    creator_id: str = "douyin_macro_investor"
    title: str
    video_url: Optional[str] = None
    publish_date: Optional[str] = None
    duration_seconds: Optional[int] = 0
    review_status: str = "unreviewed"
    transcript_checksum: Optional[str] = None
    segments_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TranscriptSegment(BaseModel):
    segment_id: str
    video_id: str
    start_seconds: float
    end_seconds: float
    text: str
    confidence: Optional[float] = None
    review_status: str = "unreviewed"

class Claim(BaseModel):
    claim_id: str
    video_id: str
    source_segment_ids: List[str] = Field(default_factory=list)
    topic: str
    subtopic: Optional[str] = None
    claim_text: str
    claim_type: str = "causal_mechanism"  # factual_assertion, causal_mechanism, interpretation, forecast, conditional_forecast, historical_analogy, risk_warning
    mechanism: Optional[str] = None
    conditions: Optional[str] = None
    indicators: Optional[str] = None
    assets_affected: List[str] = Field(default_factory=list)
    time_horizon: Optional[str] = None
    confidence_expression: Optional[str] = "high"
    evidence_text: Optional[str] = None
    timestamp_range: Optional[str] = None
    review_status: str = "unreviewed"

class Framework(BaseModel):
    id: str
    title: str
    topic: str
    version: str = "1.0.0"
    status: str = "verified"
    content_markdown: str
    key_variables: List[str] = Field(default_factory=list)
    transmission_chain: Optional[str] = None
    triggers: Optional[str] = None
    source_video_ids: List[str] = Field(default_factory=list)

class CaseStudy(BaseModel):
    case_id: str
    name: str
    topic: str
    era: str
    countries: List[str] = Field(default_factory=list)
    key_indicators: List[str] = Field(default_factory=list)
    mechanisms: str
    creator_comparative_take: str
    source_video_id: Optional[str] = None
    timestamp: Optional[str] = None
    review_status: str = "verified"

class Forecast(BaseModel):
    forecast_id: str
    video_id: str
    source_segment_ids: List[str] = Field(default_factory=list)
    forecast_date: str
    target_variable: str
    direction: str  # up, down, neutral
    target_value: Optional[str] = None
    horizon: str
    conditions: Optional[str] = None
    forecast_text: str
    review_status: str = "unreviewed"
    outcome: Optional[str] = "pending"  # hit, missed, pending
    outcome_date: Optional[str] = None
    outcome_notes: Optional[str] = None

class SearchResult(BaseModel):
    record_id: str
    source_type: str  # claim, framework, case, transcript, forecast
    title: str
    content: str
    relevance_score: float
    video_id: Optional[str] = None
    publish_date: Optional[str] = None
    timestamp_range: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AttributedCitation(BaseModel):
    citation_id: str
    category: str  # creator_statement, creator_framework, ai_extrapolation, external_fact
    title: str
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    publish_date: Optional[str] = None
    timestamp: Optional[str] = None
    verbatim_quote: Optional[str] = None
    verification_status: str = "verified"

class ExpertResponse(BaseModel):
    answer_text: str
    citations: List[AttributedCitation] = Field(default_factory=list)
    retrieved_results: List[SearchResult] = Field(default_factory=list)
    model_name: str
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    uncertainty_level: str = "low"  # low, medium, high, insufficient_evidence
