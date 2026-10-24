"""
config.py
Secure, validated configuration loader with environment variable expansion.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env if present
load_dotenv()

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-([^}]*))?\}")

def expand_env_vars(raw: Any) -> Any:
    """Recursively replaces ${VAR:-default} and ${VAR} in strings."""
    if isinstance(raw, str):
        def repl(match: re.Match) -> str:
            var_name = match.group(1)
            default_val = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default_val)
        return ENV_VAR_PATTERN.sub(repl, raw)
    elif isinstance(raw, dict):
        return {k: expand_env_vars(v) for k, v in raw.items()}
    elif isinstance(raw, list):
        return [expand_env_vars(item) for item in raw]
    return raw

class AppSettings(BaseModel):
    name: str = "Horizon: Macro Investor AI Expert"
    version: str = "0.1.0"
    language: str = "zh-CN"
    environment: str = "development"

class LLMSettings(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-flash-latest"
    embedding_model: str = "gemini-embedding-001"
    temperature: float = 0.2
    max_output_tokens: int = 3000
    timeout_seconds: int = 120

class RetrievalSettings(BaseModel):
    semantic_enabled: bool = True
    keyword_enabled: bool = True
    top_k: int = 8
    min_relevance_score: float = 0.2
    max_context_tokens: int = 16000

class KnowledgeSettings(BaseModel):
    package_path: str = "./expert_pack"
    transcript_path: str = "./data/transcripts"
    index_path: str = "./data/index"
    audio_path: str = "./data/audio"
    export_path: str = "./data/exports"

class StorageSettings(BaseModel):
    database_path: str = "./data/app.db"

class SecuritySettings(BaseModel):
    authentication_required: bool = True
    allow_registration: bool = False
    session_timeout_minutes: int = 1440
    max_login_attempts: int = 5
    lockout_minutes: int = 15

class LimitsSettings(BaseModel):
    max_question_characters: int = 10000
    max_requests_per_minute: int = 10
    daily_request_limit: int = 200
    monthly_budget_usd: float = 50.0

class AppConfig(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    knowledge: KnowledgeSettings = Field(default_factory=KnowledgeSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    limits: LimitsSettings = Field(default_factory=LimitsSettings)

def load_config(config_path: str = "config.yaml") -> AppConfig:
    p = Path(config_path)
    if not p.exists():
        # Fall back to defaults
        return AppConfig()
    
    with open(p, "r", encoding="utf-8") as f:
        raw_dict = yaml.safe_load(f) or {}
        
    expanded_dict = expand_env_vars(raw_dict)
    return AppConfig(**expanded_dict)
