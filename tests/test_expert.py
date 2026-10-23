import tempfile
from pathlib import Path
from src.macro_expert.config import load_config
from src.macro_expert.cost_control import CostController
from src.macro_expert.database import Database
from src.macro_expert.expert import MacroExpertEngine
from src.macro_expert.knowledge_package import KnowledgePackageManager
from src.macro_expert.llm import MockLLMAdapter
from src.macro_expert.retrieval import HybridRetriever

def test_expert_engine_reasoning_and_citations():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test_exp.db"))
        pkg_mgr = KnowledgePackageManager("expert_pack", db)
        pkg_mgr.sync_to_database()

        config = load_config()
        retriever = HybridRetriever(db, top_k=5)
        llm = MockLLMAdapter()
        cost_ctrl = CostController(db, config.limits)
        engine = MacroExpertEngine(retriever, llm, cost_ctrl, config)

        # Query about French & US bond yields
        query = "美法国债长端收益率走高，是否会重演欧债危机？"
        resp = engine.answer_question(query)

        assert resp.answer_text is not None
        assert "核心结论" in resp.answer_text
        assert len(resp.citations) > 0
        assert resp.tokens_used > 0
        assert resp.uncertainty_level == "low"
