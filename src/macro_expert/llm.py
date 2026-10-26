"""
llm.py
Model-provider abstraction layer supporting Gemini API (google-genai) and Mock testing adapter.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional
from pydantic import BaseModel
from src.macro_expert.config import AppConfig
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.llm")

class LLMResult(BaseModel):
    text: str
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str
    estimated_cost_usd: float = 0.0

class LLMAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 3000
    ) -> LLMResult:
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 3000
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass

def resolve_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    # 1. Explicit key
    if explicit_key and str(explicit_key).strip():
        return str(explicit_key).strip().strip('"').strip("'")

    # 2. Check os.environ
    for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "gemini_api_key", "google_api_key"]:
        val = os.environ.get(k)
        if val and str(val).strip():
            return str(val).strip().strip('"').strip("'")

    # 3. Check Streamlit Cloud secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for sec_name in ["GEMINI_API_KEY", "gemini_api_key", "GOOGLE_API_KEY", "google_api_key"]:
                if sec_name in st.secrets:
                    val = str(st.secrets[sec_name]).strip().strip('"').strip("'")
                    if val:
                        os.environ["GEMINI_API_KEY"] = val
                        return val
    except Exception:
        pass

    return None

class GeminiAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-flash-latest",
        embedding_model: str = "gemini-embedding-001"
    ):
        self.api_key = resolve_api_key(api_key)
        self.model = model
        self.embedding_model = embedding_model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set. Please provide a valid Gemini API key in secrets or environment.")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 3000
    ) -> LLMResult:
        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system_instruction
        )

        candidate_models = [self.model, "gemini-flash-latest", "gemini-3.8-flash"]
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

        last_error = None
        for m in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config
                )
                text = response.text or ""
                total_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
                return LLMResult(
                    text=text,
                    tokens_used=total_tokens,
                    model=m,
                    estimated_cost_usd=round(total_tokens * 0.0000005, 6)
                )
            except Exception as e:
                logger.warning(f"Generation attempt with model '{m}' failed: {e}. Trying fallback candidate...")
                last_error = e

        logger.error(f"All candidate models failed. Last error: {last_error}")
        raise last_error

    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 3000
    ) -> Generator[str, None, None]:
        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system_instruction
        )

        candidate_models = [self.model, "gemini-flash-latest", "gemini-3.8-flash"]
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

        last_error = None
        for m in candidate_models:
            try:
                response_stream = self.client.models.generate_content_stream(
                    model=m,
                    contents=prompt,
                    config=config
                )
                yielded_any = False
                for chunk in response_stream:
                    if chunk.text:
                        yielded_any = True
                        yield chunk.text
                if yielded_any:
                    return
            except Exception as e:
                logger.warning(f"Streaming attempt with model '{m}' failed: {e}. Trying fallback candidate...")
                last_error = e

        logger.error(f"All candidate models failed for streaming. Last error: {last_error}")
        # Final fallback to non-streaming generate if streaming had issues
        res = self.generate(prompt, system_instruction, temperature, max_output_tokens)
        yield res.text

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            embeddings = []
            for text in texts:
                result = self.client.models.embed_content(
                    model=self.embedding_model,
                    contents=text
                )
                if hasattr(result, "embeddings") and result.embeddings:
                    embeddings.append(result.embeddings[0].values)
                elif hasattr(result, "embedding") and result.embedding:
                    embeddings.append(result.embedding.values)
                else:
                    embeddings.append([0.0] * 768)
            return embeddings
        except Exception as e:
            logger.warning(f"Gemini embedding error: {e}. Falling back to zero-vectors.")
            return [[0.0] * 768 for _ in texts]

class MockLLMAdapter(LLMAdapter):
    """Deterministic, zero-cost adapter for unit testing and offline development."""
    def __init__(self, canned_response: Optional[str] = None):
        self.canned_response = canned_response

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 3000
    ) -> LLMResult:
        if self.canned_response:
            resp = self.canned_response
        else:
            resp = (
                "### 核心结论\n"
                "根据创作者的宏观债务与流动性框架，长端国债收益率的攀升主要源于期限溢价上行及国债供给超载。\n\n"
                "### 适用框架与因果传导\n"
                "传导机制：巨额财政赤字放量发债 -> 一级交易商承载力见顶 -> 期限溢价被迫上升 -> 长端收益率冲高。\n\n"
                "### 【AI 推演】针对新问题的推演\n"
                "针对法国与美国长端收益率上升是否会重演欧债危机：\n"
                "1. 美法两国有别于2011年希腊，欧洲央行已设立反碎片化工具(TPI)托底。\n"
                "2. 危机更可能体现为持续的利息支出挤压财政的‘慢性失血’，而非断崖式违约。\n\n"
                "### 证伪指标与关键观测\n"
                "- 观测法德10年期国债利差是否突破100bp关口。\n"
                "- 观测隔夜逆回购(ON RRP)缓冲垫消耗速度。\n\n"
                "### 不确定性与局限说明\n"
                "创作者未在视频中对近期突发地缘政策做出直接预测，上述延伸为基于其历史框架的逻辑推导。"
            )
        return LLMResult(
            text=resp,
            tokens_used=420,
            prompt_tokens=300,
            completion_tokens=120,
            model="mock-gemini-3.8-flash",
            estimated_cost_usd=0.0
        )

    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 3000
    ) -> Generator[str, None, None]:
        res = self.generate(prompt, system_instruction, temperature, max_output_tokens)
        words = res.text.split(" ")
        for w in words:
            yield w + " "

    def embed(self, texts: List[str]) -> List[List[float]]:
        # Deterministic 16-dim pseudo-embedding
        return [[float(len(t) % 10) / 10.0] * 16 for t in texts]

def get_llm_adapter(config: AppConfig, force_mock: bool = False) -> LLMAdapter:
    api_key = resolve_api_key()
    if force_mock or not api_key:
        logger.info("Using MockLLMAdapter (No GEMINI_API_KEY detected or force_mock=True)")
        return MockLLMAdapter()
    
    preferred_model = config.llm.model or "gemini-flash-latest"
    if preferred_model == "gemini-2.5-flash":
        preferred_model = "gemini-flash-latest"

    logger.info(f"Using GeminiAdapter with model: {preferred_model}")
    return GeminiAdapter(
        api_key=api_key,
        model=preferred_model,
        embedding_model=config.llm.embedding_model
    )
