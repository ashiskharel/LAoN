#!/usr/bin/env python3
"""Ingest Nepal-related objects from the Met Collection API into data/seed/objects.json.

Met Open Access: https://metmuseum.github.io/
Images for public-domain works are CC0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "seed" / "objects.json"
BASE = "https://collectionapi.metmuseum.org/public/collection/v1"


HEADERS = {
    "User-Agent": "LAoN/0.1 (open-source research; https://github.com/local/LAoN)",
    "Accept": "application/json",
}


def search_object_ids(query: str) -> list[int]:
    with httpx.Client(timeout=60.0, headers=HEADERS) as client:
        r = client.get(f"{BASE}/search", params={"q": query, "hasImages": "true"})
        r.raise_for_status()
        return r.json().get("objectIDs") or []


def fetch_object(oid: int) -> dict | None:
    with httpx.Client(timeout=60.0, headers=HEADERS) as client:
        r = client.get(f"{BASE}/objects/{oid}")
        if r.status_code != 200:
            return None
        return r.json()


def is_nepal_related(obj: dict) -> bool:
    blob = " ".join(
        str(obj.get(k) or "")
        for k in (
            "culture",
            "period",
            "dynasty",
            "reign",
            "portfolio",
            "artistDisplayName",
            "artistDisplayBio",
            "objectName",
            "title",
            "geographyType",
            "city",
            "state",
            "county",
            "country",
            "region",
            "subregion",
            "locale",
            "locus",
            "excavation",
            "river",
            "classification",
            "tags",
            "department",
        )
    ).lower()
    # tags may be list of dicts
    tags = obj.get("tags") or []
    if isinstance(tags, list):
        blob += " " + " ".join(
            (t.get("term") or "") if isinstance(t, dict) else str(t) for t in tags
        ).lower()
    keys = ("nepal", "kathmandu", "patan", "bhaktapur", "newar", "himalayan")
    return any(k in blob for k in keys)


def to_laon(obj: dict) -> dict:
    oid = obj["objectID"]
    image_url = obj.get("primaryImageSmall") or obj.get("primaryImage") or ""
    images = []
    if image_url and obj.get("isPublicDomain"):
        images.append(
            {
                "url": image_url,
                "type": "museum",
                "license": "CC0",
                "attribution": "The Metropolitan Museum of Art",
                "source_url": obj.get("objectURL")
                or f"https://www.metmuseum.org/art/collection/search/{oid}",
                "visibility": "public",
            }
        )
    tags = []
    for t in obj.get("tags") or []:
        if isinstance(t, dict) and t.get("term"):
            tags.append(t["term"].lower().replace(" ", "-"))
    return {
        "id": f"met-{oid}",
        "titles": [obj.get("title") or f"Met object {oid}"],
        "culture": obj.get("culture") or "Nepal (Met catalog)",
        "period": obj.get("objectDate") or obj.get("period"),
        "material": obj.get("medium"),
        "dimensions": obj.get("dimensions"),
        "iconography_tags": tags[:12],
        "status": "museum",
        "original_site": {
            "place": obj.get("country") or obj.get("region") or "Nepal",
            "tole": None,
            "temple": None,
            "geo": None,
        },
        "current_location": {
            "institution": "The Metropolitan Museum of Art",
            "accession": obj.get("accessionNumber"),
            "url": obj.get("objectURL")
            or f"https://www.metmuseum.org/art/collection/search/{oid}",
            "country": "United States",
        },
        "provenance_notes": (
            "Ingested from Met Collection API Open Access data. "
            "Museum catalog presence is not a LAoN determination of illicit origin. "
            + (obj.get("creditLine") or "")
        ).strip(),
        "theft_date": None,
        "sources": [
            {
                "label": "Met Collection API",
                "url": obj.get("objectURL")
                or f"https://www.metmuseum.org/art/collection/search/{oid}",
                "citation": f"Metropolitan Museum of Art. Object {oid} (Open Access API).",
            }
        ],
        "images": images,
        "match_links": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Met Nepal-related objects")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument(
        "--queries",
        nargs="+",
        default=["Nepal", "Kathmandu", "Patan Nepal", "Newar"],
    )
    args = parser.parse_args()

    ids: list[int] = []
    for q in args.queries:
        print(f"Searching Met for: {q}")
        found = search_object_ids(q) or []
        ids.extend(found)
    # unique preserve order
    seen: set[int] = set()
    unique_ids = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique_ids.append(i)

    seed = {"version": 1, "disclaimer": "", "objects": []}
    if SEED.exists():
        seed = json.loads(SEED.read_text(encoding="utf-8"))

    by_id = {o["id"]: o for o in seed.get("objects", [])}
    added = 0
    for oid in unique_ids:
        if added >= args.limit:
            break
        laon_id = f"met-{oid}"
        if laon_id in by_id and by_id[laon_id].get("images"):
            continue
        obj = fetch_object(oid)
        if not obj or not is_nepal_related(obj):
            continue
        if not obj.get("isPublicDomain"):
            # still keep metadata-only if strongly Nepal-tagged
            pass
        record = to_laon(obj)
        by_id[record["id"]] = record
        added += 1
        print(f"  + {record['id']}: {record['titles'][0][:60]}")

    seed["objects"] = list(by_id.values())
    if not seed.get("disclaimer"):
        seed["disclaimer"] = (
            "Possible visual match data only — not a determination of legal ownership."
        )
    SEED.parent.mkdir(parents=True, exist_ok=True)
    SEED.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Done. Added/updated up to {added} Met objects. Total catalog: {len(seed['objects'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
