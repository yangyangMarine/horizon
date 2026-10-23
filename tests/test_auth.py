import tempfile
from pathlib import Path
from src.macro_expert.auth import AuthManager, hash_password, verify_password
from src.macro_expert.database import Database

def test_password_hash_and_verify():
    pwd = "SecureInvestmentPassword2026!"
    hashed, salt = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_auth_manager_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_auth.db"
        db = Database(str(db_path))
        auth_mgr = AuthManager(db, max_attempts=3, lockout_minutes=5)

        # 1. Create admin
        auth_mgr.ensure_admin_user("admin", "admin_secret_123")

        # 2. Successful login
        user = auth_mgr.authenticate("admin", "admin_secret_123", ip_address="10.0.0.1")
        assert user is not None
        assert user["username"] == "admin"
        assert user["is_admin"] is True

        # 3. Failed attempts and rate-limiting lockout
        assert auth_mgr.authenticate("admin", "bad1", ip_address="10.0.0.2") is None
        assert auth_mgr.authenticate("admin", "bad2", ip_address="10.0.0.2") is None
        assert auth_mgr.authenticate("admin", "bad3", ip_address="10.0.0.2") is None

        # 4. Now locked out
        assert auth_mgr.is_locked_out("10.0.0.2") is True
        assert auth_mgr.authenticate("admin", "admin_secret_123", ip_address="10.0.0.2") is None
