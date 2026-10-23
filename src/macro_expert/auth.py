"""
auth.py
Secure single-user and multi-user authentication with salted hashing,
brute-force rate limiting, and cryptographically secure session handling.
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import bcrypt
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.auth")

def hash_password(password: str) -> Tuple[str, str]:
    """Generates a salt and bcrypt hash for a plaintext password."""
    salt = bcrypt.gensalt(rounds=12).decode("utf-8")
    pwd_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(pwd_bytes, salt.encode("utf-8")).decode("utf-8")
    return hashed, salt

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

class AuthManager:
    def __init__(
        self,
        db: Database,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
        session_timeout_minutes: int = 1440
    ):
        self.db = db
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self.session_timeout_minutes = session_timeout_minutes

    def ensure_admin_user(self, default_username: str = "admin", default_password: str = "admin123456") -> None:
        """Creates the initial admin user if the users table is empty."""
        with self.db.session() as conn:
            cur = conn.execute("SELECT COUNT(*) AS cnt FROM users;")
            row = cur.fetchone()
            if row["cnt"] == 0:
                hashed, salt = hash_password(default_password)
                conn.execute(
                    "INSERT INTO users(username, password_hash, salt, is_admin) VALUES (?, ?, ?, 1);",
                    (default_username, hashed, salt)
                )
                logger.info(f"Default admin user '{default_username}' created.")

    def is_locked_out(self, ip_address: str) -> bool:
        """Checks if the given IP address is currently locked out due to excessive failed attempts."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=self.lockout_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        with self.db.session() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*) as failed_count 
                FROM login_attempts 
                WHERE ip_address = ? AND success = 0 AND attempted_at > ?;
                """,
                (ip_address, cutoff)
            )
            row = cur.fetchone()
            return row["failed_count"] >= self.max_attempts

    def record_attempt(self, ip_address: str, username: str, success: bool) -> None:
        """Records a login attempt for audit and rate-limiting."""
        with self.db.session() as conn:
            conn.execute(
                "INSERT INTO login_attempts(ip_address, username, success) VALUES (?, ?, ?);",
                (ip_address, username, 1 if success else 0)
            )

    def authenticate(self, username: str, password: str, ip_address: str = "127.0.0.1") -> Optional[dict]:
        """Authenticates user credentials with rate-limiting protection."""
        if self.is_locked_out(ip_address):
            logger.warning(f"Login rejected: IP {ip_address} is temporarily locked out.")
            return None

        with self.db.session() as conn:
            cur = conn.execute(
                "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?;",
                (username,)
            )
            user_row = cur.fetchone()

        if not user_row:
            self.record_attempt(ip_address, username, success=False)
            return None

        is_valid = verify_password(password, user_row["password_hash"])
        self.record_attempt(ip_address, username, success=is_valid)

        if is_valid:
            logger.info(f"User '{username}' successfully authenticated.")
            return {
                "id": user_row["id"],
                "username": user_row["username"],
                "is_admin": bool(user_row["is_admin"])
            }
        return None

    def change_password(self, username: str, new_password: str) -> bool:
        """Updates the password for a specified user."""
        hashed, salt = hash_password(new_password)
        with self.db.session() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?;",
                (hashed, salt, username)
            )
            return cur.rowcount > 0

    def generate_session_token(self) -> str:
        """Generates a high-entropy session token."""
        return secrets.token_hex(32)
