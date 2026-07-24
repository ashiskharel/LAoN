#!/usr/bin/env python3
"""Ingest Nepal-related rows from Met Open Access CSV on GitHub (more reliable than live API).

Source: https://github.com/metmuseum/openaccess
CSV is large; we stream-filter for Nepal/Kathmandu/etc.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "seed" / "objects.json"
CSV_URL = (
    "https://media.githubusercontent.com/media/metmuseum/openaccess/master/MetObjects.csv"
)
# Fallback smaller raw path sometimes used:
CSV_URL_ALT = (
    "https://raw.githubusercontent.com/metmuseum/openaccess/master/MetObjects.csv"
)

HEADERS = {
    "User-Agent": "LAoN/0.1 (open-source research)",
    "Accept": "text/csv,*/*",
}

KEYS = ("nepal", "kathmandu", "patan", "bhaktapur", "newar")


def row_blob(row: dict) -> str:
    return " ".join(str(v or "") for v in row.values()).lower()


def nepalish(row: dict) -> bool:
    return any(k in row_blob(row) for k in KEYS)


def to_laon(row: dict) -> dict:
    oid = row.get("Object ID") or row.get("ObjectID") or "unknown"
    title = row.get("Title") or f"Met object {oid}"
    is_pd = str(row.get("Is Public Domain") or "").strip().lower() in {
        "true",
        "1",
        "yes",
    }
    # CSV does not always include image URL; store metadata + collection link
    link = row.get("Link Resource") or f"https://www.metmuseum.org/art/collection/search/{oid}"
    images = []
    # Optional image URL columns vary by export version
    for col in ("primaryImageSmall", "primaryImage", "Image URL"):
        if row.get(col) and is_pd:
            images.append(
                {
                    "url": row[col],
                    "type": "museum",
                    "license": "CC0",
                    "attribution": "The Metropolitan Museum of Art",
                    "source_url": link,
                    "visibility": "public",
                }
            )
            break
    return {
        "id": f"met-{oid}",
        "titles": [title],
        "culture": row.get("Culture") or "Nepal (Met catalog)",
        "period": row.get("Object Date") or row.get("Period"),
        "material": row.get("Medium"),
        "dimensions": row.get("Dimensions"),
        "iconography_tags": [],
        "status": "museum",
        "original_site": {
            "place": row.get("Country") or row.get("Region") or "Nepal",
            "tole": None,
            "temple": None,
            "geo": None,
        },
        "current_location": {
            "institution": "The Metropolitan Museum of Art",
            "accession": row.get("Accession Number"),
            "url": link,
            "country": "United States",
        },
        "provenance_notes": (
            "Ingested from Met Open Access CSV. "
            "Catalog presence is not a LAoN determination of illicit origin. "
            f"{row.get('Credit Line') or ''}"
        ).strip(),
        "theft_date": None,
        "sources": [
            {
                "label": "Met Open Access CSV",
                "url": link,
                "citation": f"Metropolitan Museum of Art. Object {oid} (Open Access dataset).",
            }
        ],
        "images": images,
        "match_links": [],
    }


def download_csv(url: str) -> str:
    with httpx.Client(timeout=120.0, headers=HEADERS, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Local MetObjects.csv path (skip download)",
    )
    args = parser.parse_args()

    if args.csv and args.csv.exists():
        text = args.csv.read_text(encoding="utf-8", errors="replace")
        print(f"Reading local {args.csv}")
    else:
        print("Downloading Met Open Access CSV (large)…")
        try:
            text = download_csv(CSV_URL)
        except Exception as e:
            print(f"Primary URL failed ({e}); trying alt…")
            text = download_csv(CSV_URL_ALT)

    reader = csv.DictReader(io.StringIO(text))
    seed = {"version": 1, "disclaimer": "", "objects": []}
    if SEED.exists():
        seed = json.loads(SEED.read_text(encoding="utf-8"))
    by_id = {o["id"]: o for o in seed.get("objects", [])}

    added = 0
    for row in reader:
        if not nepalish(row):
            continue
        rec = to_laon(row)
        # Prefer keeping existing richer records (e.g. with images from API)
        existing = by_id.get(rec["id"])
        if existing and existing.get("images") and not rec.get("images"):
            continue
        by_id[rec["id"]] = rec if not existing else {**existing, **{k: v for k, v in rec.items() if v}}
        # simpler: overwrite with rec but preserve images if better
        if existing and existing.get("images") and not rec.get("images"):
            by_id[rec["id"]] = existing
        else:
            by_id[rec["id"]] = rec
        added += 1
        print(f"  + {rec['id']}: {rec['titles'][0][:60]}")
        if added >= args.limit:
            break

    seed["objects"] = list(by_id.values())
    if not seed.get("disclaimer"):
        seed["disclaimer"] = (
            "Possible visual match data only — not a determination of legal ownership."
        )
    SEED.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Done. Matched {added} Nepal-related rows. Total catalog: {len(seed['objects'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
