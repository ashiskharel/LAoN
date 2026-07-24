#!/usr/bin/env python3
"""Ingest Nepal-related objects from Cleveland Museum of Art Open Access API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "seed" / "objects.json"
BASE = "https://openaccess-api.clevelandart.org/api/artworks/"


HEADERS = {
    "User-Agent": "LAoN/0.1 (open-source research; https://github.com/local/LAoN)",
    "Accept": "application/json",
}


def search(q: str, skip: int = 0, limit: int = 50) -> list[dict]:
    with httpx.Client(timeout=60.0, headers=HEADERS) as client:
        r = client.get(
            BASE,
            params={"q": q, "has_image": 1, "cc0": 1, "skip": skip, "limit": limit},
        )
        r.raise_for_status()
        return r.json().get("data") or []


def to_laon(item: dict) -> dict | None:
    cid = item.get("id") or item.get("accession_number")
    if not cid:
        return None
    title = item.get("title") or f"CMA {cid}"
    images = []
    img = item.get("images") or {}
    web = (img.get("web") or {}).get("url") if isinstance(img, dict) else None
    if web:
        images.append(
            {
                "url": web,
                "type": "museum",
                "license": "CC0",
                "attribution": "Cleveland Museum of Art",
                "source_url": item.get("url")
                or f"https://www.clevelandart.org/art/{item.get('accession_number')}",
                "visibility": "public",
            }
        )
    culture = item.get("culture")
    if isinstance(culture, list):
        culture = ", ".join(str(c) for c in culture)
    dims = item.get("measurements") or item.get("dimensions")
    if isinstance(dims, dict):
        dims = dims.get("summary") or dims.get("value") or str(dims)
    elif dims is not None and not isinstance(dims, str):
        dims = str(dims)
    material = item.get("technique") or item.get("type")
    if isinstance(material, list):
        material = ", ".join(str(m) for m in material)
    return {
        "id": f"cma-{str(cid).replace('.', '-').replace(' ', '-').lower()}",
        "titles": [title],
        "culture": culture or "Nepal",
        "period": item.get("creation_date") or item.get("date_text"),
        "material": material,
        "dimensions": dims,
        "iconography_tags": [],
        "status": "museum",
        "original_site": {
            "place": "Nepal",
            "tole": None,
            "temple": None,
            "geo": None,
        },
        "current_location": {
            "institution": "Cleveland Museum of Art",
            "accession": item.get("accession_number"),
            "url": item.get("url")
            or f"https://www.clevelandart.org/art/{item.get('accession_number')}",
            "country": "United States",
        },
        "provenance_notes": (
            "Ingested from CMA Open Access API (CC0). "
            "Catalog presence is not a LAoN determination of illicit origin."
        ),
        "theft_date": None,
        "sources": [
            {
                "label": "Cleveland Museum of Art Open Access",
                "url": item.get("url"),
                "citation": f"Cleveland Museum of Art. {title} ({item.get('accession_number')}).",
            }
        ],
        "images": images,
        "match_links": [],
    }


def nepalish(item: dict) -> bool:
    blob = json.dumps(item).lower()
    return any(
        k in blob
        for k in ("nepal", "kathmandu", "patan", "bhaktapur", "newar", "himalayan")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--query", default="Nepal")
    args = parser.parse_args()

    print(f"Searching CMA Open Access for: {args.query}")
    items = search(args.query, limit=max(args.limit * 2, 50))
    items = [i for i in items if nepalish(i)][: args.limit]

    seed = {"version": 1, "disclaimer": "", "objects": []}
    if SEED.exists():
        seed = json.loads(SEED.read_text(encoding="utf-8"))
    by_id = {o["id"]: o for o in seed.get("objects", [])}

    added = 0
    for item in items:
        rec = to_laon(item)
        if not rec:
            continue
        by_id[rec["id"]] = rec
        added += 1
        print(f"  + {rec['id']}: {rec['titles'][0][:60]}")

    seed["objects"] = list(by_id.values())
    if not seed.get("disclaimer"):
        seed["disclaimer"] = (
            "Possible visual match data only — not a determination of legal ownership."
        )
    SEED.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Done. {added} CMA objects. Total: {len(seed['objects'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
