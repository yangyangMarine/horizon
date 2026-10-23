import tempfile
from pathlib import Path
from src.macro_expert.database import Database

def test_database_init_and_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_app.db"
        db = Database(str(db_path))

        with db.session() as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r["name"] for r in cur.fetchall()]
            assert "users" in tables
            assert "videos" in tables
            assert "claims" in tables
            assert "frameworks" in tables
            assert "conversations" in tables
            assert "messages" in tables
