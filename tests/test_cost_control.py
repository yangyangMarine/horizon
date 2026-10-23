import tempfile
from pathlib import Path
from src.macro_expert.config import LimitsSettings
from src.macro_expert.cost_control import CostController
from src.macro_expert.database import Database

def test_cost_control_limits():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test_cost.db"))
        limits = LimitsSettings(
            max_question_characters=50,
            daily_request_limit=2,
            monthly_budget_usd=1.0
        )
        ctrl = CostController(db, limits)

        # 1. Normal question passes
        ok, err = ctrl.validate_request("短期美债走势如何？")
        assert ok is True
        assert err is None

        # 2. Too long question fails
        long_q = "A" * 60
        ok2, err2 = ctrl.validate_request(long_q)
        assert ok2 is False
        assert "超过最大限制" in err2

        # 3. Exceed daily requests
        ctrl.record_usage("query", "mock", 100, 50, 150, 0.05)
        ctrl.record_usage("query", "mock", 100, 50, 150, 0.05)
        ok3, err3 = ctrl.validate_request("第三次提问")
        assert ok3 is False
        assert "已达每日请求上限" in err3
