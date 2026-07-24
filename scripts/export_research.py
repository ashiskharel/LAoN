#!/usr/bin/env python3
"""CLI: export local research captures for matching."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app import research_db  # noqa: E402


def main() -> int:
    research_db.init_db()
    n_img = research_db.export_private_corpus_links()
    n_meta = research_db.sync_metadata_to_seed(include_private_image_urls=False)
    print(f"Images copied to data/private/bangdel: {n_img}")
    print(f"Metadata rows merged into seed: {n_meta}")
    print("Next: python scripts/embed_corpus.py")
    print(f"DB: {research_db.DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
