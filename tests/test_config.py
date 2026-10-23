import os
from src.macro_expert.config import load_config, expand_env_vars

def test_expand_env_vars():
    os.environ["TEST_HORIZON_VAR"] = "horizon_value"
    res = expand_env_vars("${TEST_HORIZON_VAR:-default}")
    assert res == "horizon_value"

    res_default = expand_env_vars("${NON_EXISTENT_VAR:-fallback_val}")
    assert res_default == "fallback_val"

def test_load_config():
    config = load_config("config.yaml")
    assert config.app.name.startswith("Horizon")
    assert config.llm.provider in ["gemini", "openai"]
    assert config.security.authentication_required is True
    assert config.limits.max_question_characters > 0
