"""
framework_builder.py
Synthesizes topic-level analytical frameworks from clusters of atomic claims.
"""

from pathlib import Path
from typing import List, Optional
from src.macro_expert.database import Database
from src.macro_expert.llm import LLMAdapter
from src.macro_expert.logging_config import setup_logger
from src.macro_expert.models import Claim, Framework

logger = setup_logger("horizon.framework_builder")

class FrameworkBuilder:
    def __init__(self, db: Database, llm: LLMAdapter, package_dir: str = "./expert_pack"):
        self.db = db
        self.llm = llm
        self.package_dir = Path(package_dir)
        self.frameworks_dir = self.package_dir / "frameworks"
        self.frameworks_dir.mkdir(parents=True, exist_ok=True)

    def update_or_create_topic_framework(self, topic: str, claims: List[Claim]) -> Optional[Framework]:
        if not claims:
            return None

        fw_id = f"fw_{topic}"
        md_file = self.frameworks_dir / f"{topic}.md"

        claims_summary = "\n".join([f"- [{c.claim_id}] ({c.claim_type}): {c.claim_text}" for c in claims[:10]])
        
        prompt = (
            f"You are a senior macroeconomic analyst. Synthesize or update the analytical framework for topic: {topic}.\n"
            f"Based on the following newly extracted atomic claims:\n"
            f"{claims_summary}\n\n"
            "Format the output as clean Markdown with:\n"
            "# 框架：[主题名称]\n"
            "- ID: [fw_id]\n"
            "- Topic: [topic]\n"
            "- Version: 1.1.0\n"
            "- Status: verified\n\n"
            "## 1. 核心论点 (Core Thesis)\n"
            "## 2. 关键变量 (Key Variables)\n"
            "## 3. 因果传导链条 (Causal Transmission Chain)\n"
            "## 4. 关键触发与证伪条件 (Triggers & Falsification Conditions)\n"
        )

        llm_res = self.llm.generate(prompt, max_output_tokens=2500)
        content_md = llm_res.text

        # Save to expert_pack
        md_file.write_text(content_md, encoding="utf-8")

        framework = Framework(
            id=fw_id,
            title=f"框架：{topic}",
            topic=topic,
            version="1.1.0",
            status="verified",
            content_markdown=content_md
        )

        with self.db.session() as conn:
            conn.execute(
                """
                INSERT INTO frameworks(id, title, topic, version, status, content_markdown)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET content_markdown = excluded.content_markdown;
                """,
                (framework.id, framework.title, framework.topic, framework.version, framework.status, framework.content_markdown)
            )

        logger.info(f"Updated framework {fw_id} for topic {topic}.")
        return framework
