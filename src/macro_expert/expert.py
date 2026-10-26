"""
expert.py
Expert Reasoning Engine (Layer B). Coordinates intent classification,
evidence retrieval, reasoning execution, citation attribution, and uncertainty calibration.
"""

import re
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple
from src.macro_expert.citations import build_citation_from_search_result
from src.macro_expert.config import AppConfig
from src.macro_expert.cost_control import CostController
from src.macro_expert.llm import LLMAdapter
from src.macro_expert.logging_config import setup_logger
from src.macro_expert.models import AttributedCitation, ExpertResponse, SearchResult
from src.macro_expert.retrieval import HybridRetriever

logger = setup_logger("horizon.expert")

DEFAULT_SYSTEM_PROMPT = """You are an evidence-grounded Macroeconomic and Investment Expert Assistant.
Follow strictly the four tiers of attribution:
1. 创作者原话 (Creator Explicit Statement): Must cite source video title, date, timestamp.
2. 创作者分析框架 (Creator Analytical Framework): Methodological synthesis.
3. AI 推演与延伸 (AI Extrapolation): Explicitly label as 【AI 推演】 when reasoning on new scenarios.
4. 外部客观事实 (External Evidence).

If evidence is insufficient or the creator has not discussed the subject:
State clearly: "创作者在现有已收录视频中未直接讨论该具体标的/事件。"
Never fabricate citations, timestamps, or quotes.
"""

class MacroExpertEngine:
    def __init__(
        self,
        retriever: HybridRetriever,
        llm: LLMAdapter,
        cost_controller: CostController,
        config: AppConfig,
        prompts_dir: str = "prompts"
    ):
        self.retriever = retriever
        self.llm = llm
        self.cost_controller = cost_controller
        self.config = config
        self.prompts_dir = Path(prompts_dir)
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        analyst_file = self.prompts_dir / "analyst.md"
        if analyst_file.exists():
            return analyst_file.read_text(encoding="utf-8")
        return DEFAULT_SYSTEM_PROMPT

    def answer_question(
        self,
        question: str,
        topic: Optional[str] = None,
        top_k: int = 6,
        system_prompt: Optional[str] = None
    ) -> ExpertResponse:
        # 1. Cost and safety validation
        valid, err_msg = self.cost_controller.validate_request(question)
        if not valid:
            return ExpertResponse(
                answer_text=f"⚠️ 请求受阻: {err_msg}",
                model_name="policy_guard",
                uncertainty_level="high"
            )

        # 2. Retrieve relevant evidence
        search_results = self.retriever.search(query=question, topic=topic, top_k=top_k)

        # 3. Assess evidence sufficiency
        has_relevant_evidence = len(search_results) > 0 and search_results[0].relevance_score >= 0.25
        uncertainty = "low" if has_relevant_evidence else "insufficient_evidence"

        # 4. Build prompt context
        evidence_blocks = []
        citations: List[AttributedCitation] = []
        for res in search_results:
            citation = build_citation_from_search_result(res)
            citations.append(citation)

            meta = res.metadata or {}
            vid_info = f" [视频ID: {res.video_id}, 时间戳: {res.timestamp_range or '未标注'}]" if res.video_id else ""
            evidence_blocks.append(
                f"### [来源 {res.source_type.upper()}: {res.title}]{vid_info}\n{res.content}\n"
            )

        context_str = "\n".join(evidence_blocks) if evidence_blocks else "（未检索到高度相关的创作者历史记录）"
        augmented_prompt = self._build_augmented_prompt(question, context_str)

        # 5. Invoke LLM
        effective_sys_prompt = system_prompt or self.system_prompt
        llm_result = self.llm.generate(
            prompt=augmented_prompt,
            system_instruction=effective_sys_prompt,
            temperature=self.config.llm.temperature,
            max_output_tokens=self.config.llm.max_output_tokens
        )

        # 6. Record usage
        self.cost_controller.record_usage(
            operation="chat_query",
            model=llm_result.model,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            total_tokens=llm_result.tokens_used,
            estimated_cost_usd=llm_result.estimated_cost_usd
        )

        return ExpertResponse(
            answer_text=llm_result.text,
            citations=citations,
            retrieved_results=search_results,
            model_name=llm_result.model,
            tokens_used=llm_result.tokens_used,
            estimated_cost_usd=llm_result.estimated_cost_usd,
            uncertainty_level=uncertainty
        )

    def _build_augmented_prompt(self, question: str, context_str: str) -> str:
        is_greeting = bool(
            re.match(
                r"^\s*(hi|hello|hey|你好|您好|哈喽|在吗|早|早上好|晚上好|在不在|who are you|你是谁|介绍一下你自己|自我介绍)\s*[!！?？。.]*\s*$",
                question.strip(),
                re.IGNORECASE
            )
        )
        greeting_instruction = ""
        if is_greeting:
            greeting_instruction = (
                "\n【特别注意】：用户当前仅为日常礼貌问候或自我介绍询问。"
                "请以亲切自然、干练专业的顶级投资专家口吻简短回应（控制在 80 字以内），"
                "简要介绍本专家专注的研判领域，并热情邀请用户提出具体的宏观、流动性、估值或个股投资问题。"
                "切勿套用长篇宏观投研报告框架，直接快速作答！"
            )

        return (
            f"用户提出的问题：\n{question}\n\n"
            f"=== 以下为检索到的创作者相关知识库记录（事实证据） ===\n"
            f"{context_str}\n"
            f"=== 结束知识库记录 ===\n\n"
            "请基于以上证据和系统准则回答用户的问题。\n"
            "要求：\n"
            "1. 严格区分创作者原话、创作者框架、以及针对新情境的【AI 推演】。\n"
            "2. 若资料中未提及相关内容，如实告知‘创作者在收录视频中未直接提及’。\n"
            "3. 保持客观理性、严谨求实的宏观投研风格。"
            f"{greeting_instruction}"
        )

    def stream_question(
        self,
        question: str,
        topic: Optional[str] = None,
        top_k: int = 6,
        system_prompt: Optional[str] = None
    ) -> Tuple[List[AttributedCitation], List[SearchResult], Generator[str, None, None]]:
        # 1. Cost and safety validation
        valid, err_msg = self.cost_controller.validate_request(question)
        if not valid:
            def err_gen():
                yield f"⚠️ 请求受阻: {err_msg}"
            return [], [], err_gen()

        # 2. Retrieve relevant evidence
        search_results = self.retriever.search(query=question, topic=topic, top_k=top_k)

        # 3. Build citations & evidence blocks
        evidence_blocks = []
        citations: List[AttributedCitation] = []
        for res in search_results:
            citation = build_citation_from_search_result(res)
            citations.append(citation)

            meta = res.metadata or {}
            vid_info = f" [视频ID: {res.video_id}, 时间戳: {res.timestamp_range or '未标注'}]" if res.video_id else ""
            evidence_blocks.append(
                f"### [来源 {res.source_type.upper()}: {res.title}]{vid_info}\n{res.content}\n"
            )

        context_str = "\n".join(evidence_blocks) if evidence_blocks else "（未检索到高度相关的创作者历史记录）"
        augmented_prompt = self._build_augmented_prompt(question, context_str)
        effective_sys_prompt = system_prompt or self.system_prompt

        stream_gen = self.llm.generate_stream(
            prompt=augmented_prompt,
            system_instruction=effective_sys_prompt,
            temperature=self.config.llm.temperature,
            max_output_tokens=self.config.llm.max_output_tokens
        )
        return citations, search_results, stream_gen
