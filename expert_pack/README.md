# Portable Expert Knowledge Package (专家知识包)

This package contains the distilled analytical knowledge, atomic claims, frameworks, historical case studies, forecasts, and source catalogs for the Macro Investor Expert.

## Portability Specification
- **Self-contained**: All metadata, evidence references, and schemas can be parsed independently of any database or UI.
- **Reproducible**: Can be verified with `scripts/validate_package.py` and exported to a portable ZIP package via `scripts/export_package.py`.
- **Integrity**: Every file hash is cataloged in `manifest.yaml` with SHA-256.
