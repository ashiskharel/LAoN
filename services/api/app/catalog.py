from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from .config import SEED_PATH, GEO_PATH, DISCLAIMER
from .models import CulturalObject


@lru_cache(maxsize=1)
def load_raw_seed() -> dict:
    if not SEED_PATH.exists():
        return {"version": 1, "objects": [], "disclaimer": DISCLAIMER}
    with SEED_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def reload_catalog() -> None:
    load_raw_seed.cache_clear()


def _as_optional_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        # CMA sometimes returns structured measurement blobs
        for key in ("summary", "value", "text", "display"):
            if value.get(key):
                return str(value[key])
        try:
            import json

            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v is not None)
    return str(value)


def all_objects() -> list[CulturalObject]:
    raw = load_raw_seed()
    objects: list[CulturalObject] = []
    for item in raw.get("objects", []):
        # Filter private images from public API responses
        images = [
            img
            for img in item.get("images") or []
            if img.get("visibility", "public") == "public"
        ]
        data = {**item, "images": images}
        for field in ("dimensions", "material", "period", "culture", "theft_date"):
            if field in data:
                data[field] = _as_optional_str(data.get(field))
        objects.append(CulturalObject.model_validate(data))
    return objects


def get_object(object_id: str) -> Optional[CulturalObject]:
    for obj in all_objects():
        if obj.id == object_id:
            return obj
    return None


def search_objects(
    q: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    place: Optional[str] = None,
) -> list[CulturalObject]:
    results = all_objects()
    if status:
        results = [o for o in results if o.status == status]
    if tag:
        t = tag.lower()
        results = [
            o
            for o in results
            if any(t in (x or "").lower() for x in o.iconography_tags)
        ]
    if place:
        p = place.lower()

        def place_match(o: CulturalObject) -> bool:
            site = o.original_site
            if not site:
                return False
            hay = " ".join(
                filter(
                    None,
                    [site.place, site.tole, site.temple],
                )
            ).lower()
            return p in hay

        results = [o for o in results if place_match(o)]
    if q:
        needle = q.lower()

        def text_match(o: CulturalObject) -> bool:
            parts: list[str] = []
            parts.extend(o.titles)
            parts.extend(o.iconography_tags)
            if o.culture:
                parts.append(o.culture)
            if o.period:
                parts.append(o.period)
            if o.material:
                parts.append(o.material)
            if o.provenance_notes:
                parts.append(o.provenance_notes)
            if o.original_site:
                parts.extend(
                    filter(
                        None,
                        [
                            o.original_site.place,
                            o.original_site.tole,
                            o.original_site.temple,
                        ],
                    )
                )
            if o.current_location and o.current_location.institution:
                parts.append(o.current_location.institution)
            blob = " ".join(parts).lower()
            return needle in blob

        results = [o for o in results if text_match(o)]
    return results


def load_geojson() -> dict:
    if not GEO_PATH.exists():
        return {"type": "FeatureCollection", "features": []}
    with GEO_PATH.open(encoding="utf-8") as f:
        return json.load(f)
