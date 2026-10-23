"""
logging_config.py
Secure, structured logging setup. Ensures credentials and tokens are redacted.
"""

import logging
import re
import sys

# Redaction patterns for secrets
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)(['\"])?([A-Za-z0-9_\-]{8,})(['\"])?", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*)(['\"])?([^\s'\"]+)(['\"])?", re.IGNORECASE),
    re.compile(r"(session[_-]?secret\s*[:=]\s*)(['\"])?([A-Za-z0-9_\-]{8,})(['\"])?", re.IGNORECASE),
]

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub(r"\1\2[REDACTED]\4", redacted)
        return redacted

def setup_logger(name: str = "horizon", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
