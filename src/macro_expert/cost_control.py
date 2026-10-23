"""
cost_control.py
Cost, token, and request-budget guardrails with SQLite usage tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from src.macro_expert.config import LimitsSettings
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.cost_control")

class CostController:
    def __init__(self, db: Database, limits: LimitsSettings):
        self.db = db
        self.limits = limits

    def validate_request(self, question: str) -> Tuple[bool, Optional[str]]:
        """Validates request size and rate limits before calling the LLM."""
        if len(question) > self.limits.max_question_characters:
            return False, f"提问长度超过最大限制 ({len(question)} > {self.limits.max_question_characters} 字符)"

        # Check daily request count
        start_of_day = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
        with self.db.session() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) as cnt FROM usage_events WHERE created_at >= ?;",
                (start_of_day,)
            )
            daily_cnt = cur.fetchone()["cnt"]
            if daily_cnt >= self.limits.daily_request_limit:
                return False, f"已达每日请求上限 ({daily_cnt}/{self.limits.daily_request_limit})"

        # Check monthly budget
        start_of_month = datetime.now(timezone.utc).strftime("%Y-%m-01 00:00:00")
        with self.db.session() as conn:
            cur = conn.execute(
                "SELECT COALESCE(SUM(estimated_cost_usd), 0.0) as month_cost FROM usage_events WHERE created_at >= ?;",
                (start_of_month,)
            )
            month_cost = cur.fetchone()["month_cost"]
            if month_cost >= self.limits.monthly_budget_usd:
                return False, f"已达当月预算上限 (${month_cost:.2f} >= ${self.limits.monthly_budget_usd:.2f})"

        return True, None

    def record_usage(
        self,
        operation: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        request_id: Optional[str] = None
    ) -> None:
        with self.db.session() as conn:
            conn.execute(
                """
                INSERT INTO usage_events(request_id, operation, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (request_id, operation, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd)
            )

    def get_usage_summary(self) -> Dict[str, float]:
        start_of_month = datetime.utcnow().strftime("%Y-%m-01 00:00:00")
        start_of_day = datetime.utcnow().strftime("%Y-%m-%d 00:00:00")
        with self.db.session() as conn:
            cur_month = conn.execute(
                "SELECT COALESCE(SUM(total_tokens), 0) as tokens, COALESCE(SUM(estimated_cost_usd), 0.0) as cost FROM usage_events WHERE created_at >= ?;",
                (start_of_month,)
            )
            month_row = cur_month.fetchone()
            cur_day = conn.execute(
                "SELECT COUNT(*) as reqs, COALESCE(SUM(estimated_cost_usd), 0.0) as cost FROM usage_events WHERE created_at >= ?;",
                (start_of_day,)
            )
            day_row = cur_day.fetchone()

            return {
                "today_requests": day_row["reqs"],
                "today_cost_usd": round(day_row["cost"], 4),
                "monthly_tokens": month_row["tokens"],
                "monthly_cost_usd": round(month_row["cost"], 4),
                "monthly_budget_usd": self.limits.monthly_budget_usd
            }
