import tempfile
from pathlib import Path
from src.macro_expert.database import Database
from src.macro_expert.knowledge_package import KnowledgePackageManager
from src.macro_expert.retrieval import HybridRetriever

def test_hybrid_retrieval_and_fts():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test_ret.db"))
        # Sync knowledge pack
        pkg_mgr = KnowledgePackageManager("expert_pack", db)
        pkg_mgr.sync_to_database()

        retriever = HybridRetriever(db, top_k=5)

        # 1. Exact terminology query
        res1 = retriever.search("净流动性 逆回购 TGA")
        assert len(res1) > 0
        top_ids = [r.record_id for r in res1]
        assert any("liquidity" in r.record_id or "006" in r.record_id or "007" in r.record_id for r in res1)

        # 2. Sovereign debt query
        res2 = retriever.search("法国国债 欧债危机 2011")
        assert len(res2) > 0
        assert any("002" in r.record_id or "sovereign" in r.record_id or "case_001" in r.record_id for r in res2)
