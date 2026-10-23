import tempfile
import zipfile
from pathlib import Path
from src.macro_expert.database import Database
from src.macro_expert.export import ExportManager
from src.macro_expert.knowledge_package import KnowledgePackageManager
from scripts.validate_package import generate_or_validate_manifest

def test_package_validation_and_export_roundtrip():
    pkg_dir = Path("expert_pack")
    assert generate_or_validate_manifest(pkg_dir, update=False) is True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_export_dir = Path(tmpdir) / "exports"
        export_mgr = ExportManager(
            package_dir=str(pkg_dir),
            export_dir=str(tmp_export_dir)
        )

        # Export ZIP
        zip_path = export_mgr.export_expert_package_zip("test_pack.zip")
        assert zip_path.exists()
        assert zipfile.is_zipfile(zip_path)

        # Verify ZIP contains manifest and frameworks
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.yaml" in names
            assert "identity.md" in names
            assert any(n.startswith("frameworks/") for n in names)
            assert any(n.startswith("claims/") for n in names)

        # Import into clean DB
        clean_db = Database(str(Path(tmpdir) / "clean.db"))
        pkg_mgr = KnowledgePackageManager(str(pkg_dir), clean_db)
        counts = pkg_mgr.sync_to_database()
        assert counts["claims"] > 0
        assert counts["frameworks"] > 0
        assert counts["fts_indexed"] > 0
