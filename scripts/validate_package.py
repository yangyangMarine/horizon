#!/usr/bin/env python3
"""
validate_package.py
Validates the structure, JSONL syntax, and SHA-256 checksums of the Expert Knowledge Package.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
import yaml

def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def validate_jsonl(filepath: Path) -> int:
    if not filepath.exists():
        raise FileNotFoundError(f"Missing required JSONL file: {filepath}")
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                count += 1
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at {filepath}:{idx} - {e}")
    return count

def generate_or_validate_manifest(package_dir: Path, update: bool = False) -> bool:
    manifest_path = package_dir / "manifest.yaml"
    required_files = [
        "identity.md",
        "reasoning_rules.md",
        "answer_policy.md",
        "sources/source_catalog.jsonl",
        "claims/claims.jsonl",
        "cases/cases.jsonl",
        "forecasts/forecasts.jsonl",
        "evaluation/test_questions.jsonl",
    ]

    # Count items
    counts = {
        "sources": validate_jsonl(package_dir / "sources/source_catalog.jsonl"),
        "claims": validate_jsonl(package_dir / "claims/claims.jsonl"),
        "cases": validate_jsonl(package_dir / "cases/cases.jsonl"),
        "forecasts": validate_jsonl(package_dir / "forecasts/forecasts.jsonl"),
        "evaluation_questions": validate_jsonl(package_dir / "evaluation/test_questions.jsonl"),
    }

    framework_files = list((package_dir / "frameworks").glob("*.md"))
    counts["frameworks"] = len(framework_files)

    checksums = {}
    for rel_path in required_files:
        p = package_dir / rel_path
        if not p.exists():
            raise FileNotFoundError(f"Missing expected file: {p}")
        checksums[rel_path] = compute_sha256(p)

    for fw in framework_files:
        rel_path = f"frameworks/{fw.name}"
        checksums[rel_path] = compute_sha256(fw)

    manifest_data = {
        "package_name": "horizon-macro-expert-pack",
        "schema_version": "1.0.0",
        "package_version": "1.0.0",
        "author": "Horizon",
        "description": "Distilled macroeconomic and investment analytical frameworks from video corpus",
        "inventory": counts,
        "checksums": checksums,
        "licensing": "Private personal use. Transcripts and materials reserved."
    }

    if update or not manifest_path.exists():
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(manifest_data, f, allow_unicode=True, sort_keys=False)
        print(f"[OK] Manifest generated/updated at {manifest_path}")
        return True
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f)
        for rel_path, expected_hash in existing.get("checksums", {}).items():
            actual_hash = checksums.get(rel_path)
            if actual_hash != expected_hash:
                raise ValueError(f"Checksum mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}")
        print(f"[OK] Manifest validated successfully for {package_dir}")
        return True

if __name__ == "__main__":
    pkg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("expert_pack")
    try:
        generate_or_validate_manifest(pkg, update=True)
        print(f"Expert Knowledge Package at '{pkg}' is 100% valid.")
    except Exception as e:
        print(f"[ERROR] Validation failed: {e}", file=sys.stderr)
        sys.exit(1)
