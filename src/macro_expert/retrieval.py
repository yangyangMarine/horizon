"""
retrieval.py
Hybrid retrieval engine combining SQLite FTS5 full-text keyword search,
Chinese financial n-gram matching, and metadata filtering.
"""

import json
import re
from typing import Any, Dict, List, Optional
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger
from src.macro_expert.models import SearchResult

logger = setup_logger("horizon.retrieval")

CHINESE_STOPWORDS = {
    "是否", "如何", "怎样", "为什么", "什么", "以及", "通过", "进行", "可以",
    "可能", "我们", "这个", "那个", "虽然", "但是", "因为", "所以", "如果",
    "对于", "关于", "等等", "不仅", "而且", "其中", "或者", "还是"
}

def extract_search_terms(query: str) -> List[str]:
    """Extracts significant keywords and 2-4 character Chinese terms from queries."""
    cleaned = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", query).strip()
    terms = []

    # English / space-separated words
    for w in cleaned.split():
        if len(w) >= 2 and not re.search(r"[\u4e00-\u9fff]", w):
            terms.append(w)

    # Chinese blocks
    cjk_blocks = re.findall(r"[\u4e00-\u9fff]+", cleaned)
    for block in cjk_blocks:
        if len(block) in (2, 3, 4) and block not in CHINESE_STOPWORDS:
            terms.append(block)
        elif len(block) > 4:
            # Add 4-gram, 3-gram, 2-gram
            for length in (4, 3, 2):
                for i in range(len(block) - length + 1):
                    gram = block[i:i+length]
                    if gram not in CHINESE_STOPWORDS and gram not in terms:
                        terms.append(gram)

    return list(dict.fromkeys(terms))

class HybridRetriever:
    def __init__(self, db: Database, top_k: int = 8, min_score: float = 0.1):
        self.db = db
        self.top_k = top_k
        self.min_score = min_score

    def search(
        self,
        query: str,
        topic: Optional[str] = None,
        source_types: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        k = top_k or self.top_k
        results: List[SearchResult] = []
        seen_keys = set()
        terms = extract_search_terms(query)

        # 1. Full-Text Search via FTS5 (for terms >= 3 chars supported by trigram)
        fts_terms = [f'"{t}"' for t in terms if len(t) >= 3]
        if fts_terms:
            fts_query = " OR ".join(fts_terms[:6])
            try:
                with self.db.session() as conn:
                    sql = """
                    SELECT record_id, source_type, title, content, rank
                    FROM knowledge_fts
                    WHERE knowledge_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT ?;
                    """
                    cur = conn.execute(sql, (fts_query, k * 2))
                    for row in cur.fetchall():
                        rec_id = row["record_id"]
                        src_type = row["source_type"]
                        if source_types and src_type not in source_types:
                            continue

                        meta = self._enrich_metadata(conn, rec_id, src_type)
                        if topic and meta.get("topic") and meta.get("topic") != topic:
                            continue

                        score = max(0.3, min(1.0, 1.0 / (1.0 + abs(row["rank"]))))
                        res = SearchResult(
                            record_id=rec_id,
                            source_type=src_type,
                            title=row["title"],
                            content=row["content"],
                            relevance_score=round(score, 4),
                            video_id=meta.get("video_id"),
                            publish_date=meta.get("publish_date"),
                            timestamp_range=meta.get("timestamp_range"),
                            metadata=meta
                        )
                        results.append(res)
                        seen_keys.add((src_type, rec_id))
            except Exception as e:
                logger.warning(f"FTS5 query failed: {e}. Falling back to keyword LIKE.")

        # 2. Rich Keyword LIKE search across claims, frameworks, cases, and segments
        fallback_results = self._like_search(terms, seen_keys, limit=k)
        results.extend(fallback_results)

        # Sort by relevance score descending
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:k]

    def _enrich_metadata(self, conn, record_id: str, source_type: str) -> Dict[str, Any]:
        meta = {}
        try:
            if source_type == "claim":
                cur = conn.execute(
                    "SELECT c.*, v.video_url, v.publish_date as v_publish FROM claims c LEFT JOIN videos v ON c.video_id = v.video_id WHERE c.claim_id = ?;",
                    (record_id,)
                )
                row = cur.fetchone()
                if row:
                    meta = dict(row)
                    meta["video_url"] = row["video_url"]
                    meta["publish_date"] = row["v_publish"]
            elif source_type == "framework":
                cur = conn.execute("SELECT * FROM frameworks WHERE id = ?;", (record_id,))
                row = cur.fetchone()
                if row:
                    meta = dict(row)
            elif source_type == "case":
                cur = conn.execute("SELECT * FROM cases WHERE case_id = ?;", (record_id,))
                row = cur.fetchone()
                if row:
                    meta = dict(row)
            elif source_type == "transcript_segment":
                cur = conn.execute(
                    "SELECT s.*, v.video_url, v.publish_date FROM transcript_segments s LEFT JOIN videos v ON s.video_id = v.video_id WHERE s.segment_id = ?;",
                    (record_id,)
                )
                row = cur.fetchone()
                if row:
                    meta = dict(row)
                    meta["timestamp_range"] = f"{int(row['start_seconds'])}s - {int(row['end_seconds'])}s"
        except Exception as e:
            logger.debug(f"Metadata enrichment error: {e}")
        return meta

    def _like_search(self, terms: List[str], seen_keys: set, limit: int = 6) -> List[SearchResult]:
        found: List[SearchResult] = []
        if not terms:
            return found

        with self.db.session() as conn:
            # Check terms
            for term in terms[:8]:
                pattern = f"%{term}%"

                # 1. Search frameworks
                cur_fw = conn.execute(
                    "SELECT id, title, topic, content_markdown FROM frameworks WHERE content_markdown LIKE ? OR title LIKE ? LIMIT ?;",
                    (pattern, pattern, limit)
                )
                for r in cur_fw.fetchall():
                    key = ("framework", r["id"])
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    found.append(
                        SearchResult(
                            record_id=r["id"],
                            source_type="framework",
                            title=r["title"],
                            content=r["content_markdown"][:400],
                            relevance_score=0.82,
                            metadata=dict(r)
                        )
                    )

                # 2. Search claims
                cur = conn.execute(
                    """
                    SELECT c.claim_id, c.topic, c.claim_text, c.mechanism, c.evidence_text, c.timestamp_range, v.video_id, v.video_url, v.publish_date
                    FROM claims c
                    LEFT JOIN videos v ON c.video_id = v.video_id
                    WHERE c.claim_text LIKE ? OR c.mechanism LIKE ? OR c.evidence_text LIKE ?
                    LIMIT ?;
                    """,
                    (pattern, pattern, pattern, limit)
                )
                for row in cur.fetchall():
                    key = ("claim", row["claim_id"])
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    content = f"{row['claim_text']} {row['mechanism'] or ''} {row['evidence_text'] or ''}"
                    found.append(
                        SearchResult(
                            record_id=row["claim_id"],
                            source_type="claim",
                            title=f"主张 [{row['topic']}]",
                            content=content.strip(),
                            relevance_score=0.78,
                            video_id=row["video_id"],
                            publish_date=row["publish_date"],
                            timestamp_range=row["timestamp_range"],
                            metadata=dict(row)
                        )
                    )

                # 3. Search cases
                cur_case = conn.execute(
                    "SELECT case_id, name, mechanisms, creator_comparative_take, timestamp, source_video_id FROM cases WHERE mechanisms LIKE ? OR creator_comparative_take LIKE ? OR name LIKE ? LIMIT ?;",
                    (pattern, pattern, pattern, limit)
                )
                for r in cur_case.fetchall():
                    key = ("case", r["case_id"])
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    found.append(
                        SearchResult(
                            record_id=r["case_id"],
                            source_type="case",
                            title=r["name"],
                            content=f"{r['mechanisms']} {r['creator_comparative_take']}",
                            relevance_score=0.75,
                            video_id=r["source_video_id"],
                            timestamp_range=r["timestamp"],
                            metadata=dict(r)
                        )
                    )

                if len(found) >= limit:
                    break

        return found
