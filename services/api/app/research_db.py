"""Local SQLite research database for Bangdel plate captures and field notes.

Never commit the DB or image files. For operator machines only.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from .config import DATA_DIR

LOCAL_DIR = Path(
    __import__("os").environ.get("LAON_LOCAL_DIR", str(DATA_DIR / "local"))
)
DB_PATH = LOCAL_DIR / "research.db"
IMAGES_DIR = LOCAL_DIR / "images"
BANGDEL_DIR = IMAGES_DIR / "bangdel"


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "capture")[:max_len]


def ensure_local_dirs() -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BANGDEL_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_local_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    ensure_local_dirs()
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_captures (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                titles_json TEXT,
                culture TEXT,
                period TEXT,
                material TEXT,
                dimensions TEXT,
                iconography_tags_json TEXT,
                status TEXT NOT NULL DEFAULT 'stolen_documented',
                place TEXT,
                tole TEXT,
                temple TEXT,
                lat REAL,
                lng REAL,
                theft_date TEXT,
                bangdel_page TEXT,
                bangdel_plate TEXT,
                source_book TEXT DEFAULT 'Bangdel, Stolen Images of Nepal (1989)',
                provenance_notes TEXT,
                notes TEXT,
                image_relpath TEXT,
                image_filename TEXT,
                visibility TEXT NOT NULL DEFAULT 'private',
                linked_catalog_id TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_captures_place ON research_captures(place)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_captures_bangdel ON research_captures(bangdel_page)"
        )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["iconography_tags"] = json.loads(d.pop("iconography_tags_json") or "[]")
    d["titles"] = json.loads(d.pop("titles_json") or "[]")
    if not d["titles"] and d.get("title"):
        d["titles"] = [d["title"]]
    return d


def list_captures(
    q: Optional[str] = None,
    place: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    init_db()
    sql = "SELECT * FROM research_captures WHERE 1=1"
    params: list[Any] = []
    if place:
        sql += " AND (place LIKE ? OR tole LIKE ? OR temple LIKE ?)"
        p = f"%{place}%"
        params.extend([p, p, p])
    if q:
        sql += (
            " AND (title LIKE ? OR notes LIKE ? OR provenance_notes LIKE ?"
            " OR bangdel_page LIKE ? OR bangdel_plate LIKE ?"
            " OR iconography_tags_json LIKE ?)"
        )
        qq = f"%{q}%"
        params.extend([qq, qq, qq, qq, qq, qq])
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_capture(capture_id: str) -> Optional[dict[str, Any]]:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM research_captures WHERE id = ?", (capture_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def save_capture(
    *,
    title: str,
    image_bytes: Optional[bytes] = None,
    image_filename: Optional[str] = None,
    culture: str = "Nepal",
    period: Optional[str] = None,
    material: Optional[str] = None,
    dimensions: Optional[str] = None,
    iconography_tags: Optional[list[str]] = None,
    status: str = "stolen_documented",
    place: Optional[str] = None,
    tole: Optional[str] = None,
    temple: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    theft_date: Optional[str] = None,
    bangdel_page: Optional[str] = None,
    bangdel_plate: Optional[str] = None,
    source_book: str = "Bangdel, Lain Singh. Stolen Images of Nepal. Royal Nepal Academy, 1989.",
    provenance_notes: Optional[str] = None,
    notes: Optional[str] = None,
    capture_id: Optional[str] = None,
    linked_catalog_id: Optional[str] = None,
) -> dict[str, Any]:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    cid = capture_id or f"bangdel-{_slug(title)}-{uuid.uuid4().hex[:8]}"
    tags = iconography_tags or []
    titles = [title]

    image_relpath = None
    stored_name = None
    if image_bytes:
        ext = ".jpg"
        if image_filename and "." in image_filename:
            ext = "." + image_filename.rsplit(".", 1)[-1].lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                ext = ".jpg"
        stored_name = f"{cid}{ext}"
        dest = BANGDEL_DIR / stored_name
        dest.write_bytes(image_bytes)
        image_relpath = f"images/bangdel/{stored_name}"

    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM research_captures WHERE id = ?", (cid,)
        ).fetchone()
        if existing:
            # update metadata; keep image if no new one
            if image_relpath:
                conn.execute(
                    """
                    UPDATE research_captures SET
                      updated_at=?, title=?, titles_json=?, culture=?, period=?,
                      material=?, dimensions=?, iconography_tags_json=?, status=?,
                      place=?, tole=?, temple=?, lat=?, lng=?, theft_date=?,
                      bangdel_page=?, bangdel_plate=?, source_book=?,
                      provenance_notes=?, notes=?, image_relpath=?, image_filename=?,
                      linked_catalog_id=?
                    WHERE id=?
                    """,
                    (
                        now,
                        title,
                        json.dumps(titles),
                        culture,
                        period,
                        material,
                        dimensions,
                        json.dumps(tags),
                        status,
                        place,
                        tole,
                        temple,
                        lat,
                        lng,
                        theft_date,
                        bangdel_page,
                        bangdel_plate,
                        source_book,
                        provenance_notes,
                        notes,
                        image_relpath,
                        stored_name,
                        linked_catalog_id,
                        cid,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE research_captures SET
                      updated_at=?, title=?, titles_json=?, culture=?, period=?,
                      material=?, dimensions=?, iconography_tags_json=?, status=?,
                      place=?, tole=?, temple=?, lat=?, lng=?, theft_date=?,
                      bangdel_page=?, bangdel_plate=?, source_book=?,
                      provenance_notes=?, notes=?, linked_catalog_id=?
                    WHERE id=?
                    """,
                    (
                        now,
                        title,
                        json.dumps(titles),
                        culture,
                        period,
                        material,
                        dimensions,
                        json.dumps(tags),
                        status,
                        place,
                        tole,
                        temple,
                        lat,
                        lng,
                        theft_date,
                        bangdel_page,
                        bangdel_plate,
                        source_book,
                        provenance_notes,
                        notes,
                        linked_catalog_id,
                        cid,
                    ),
                )
        else:
            conn.execute(
                """
                INSERT INTO research_captures (
                  id, created_at, updated_at, title, titles_json, culture, period,
                  material, dimensions, iconography_tags_json, status,
                  place, tole, temple, lat, lng, theft_date,
                  bangdel_page, bangdel_plate, source_book,
                  provenance_notes, notes, image_relpath, image_filename,
                  visibility, linked_catalog_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    cid,
                    now,
                    now,
                    title,
                    json.dumps(titles),
                    culture,
                    period,
                    material,
                    dimensions,
                    json.dumps(tags),
                    status,
                    place,
                    tole,
                    temple,
                    lat,
                    lng,
                    theft_date,
                    bangdel_page,
                    bangdel_plate,
                    source_book,
                    provenance_notes,
                    notes,
                    image_relpath,
                    stored_name,
                    "private",
                    linked_catalog_id,
                ),
            )

    out = get_capture(cid)
    assert out is not None
    return out


def delete_capture(capture_id: str) -> bool:
    init_db()
    cap = get_capture(capture_id)
    if not cap:
        return False
    with connect() as conn:
        conn.execute("DELETE FROM research_captures WHERE id = ?", (capture_id,))
    rel = cap.get("image_relpath")
    if rel:
        path = LOCAL_DIR / rel
        if path.exists():
            path.unlink()
    return True


def image_path_for(capture_id: str) -> Optional[Path]:
    cap = get_capture(capture_id)
    if not cap or not cap.get("image_relpath"):
        return None
    path = LOCAL_DIR / cap["image_relpath"]
    return path if path.exists() else None


def export_private_corpus_links() -> int:
    """Copy/link captures into data/private for embed_corpus filename matching.

    Writes data/private/bangdel/<linked_or_id>.jpg and a research export JSON.
    """
    init_db()
    private_bangdel = DATA_DIR / "private" / "bangdel"
    private_bangdel.mkdir(parents=True, exist_ok=True)
    captures = list_captures(limit=5000)
    export = []
    n = 0
    for cap in captures:
        src = image_path_for(cap["id"])
        if not src:
            export.append({**cap, "export_image": None})
            continue
        # Prefer linked catalog id for embed_corpus matching
        stem = cap.get("linked_catalog_id") or cap["id"]
        dest = private_bangdel / f"{stem}{src.suffix.lower()}"
        dest.write_bytes(src.read_bytes())
        export.append({**cap, "export_image": str(dest.relative_to(DATA_DIR))})
        n += 1

    export_path = LOCAL_DIR / "captures_export.json"
    export_path.write_text(
        json.dumps(
            {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "count": len(export),
                "images_copied": n,
                "captures": export,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return n


def sync_metadata_to_seed(include_private_image_urls: bool = False) -> int:
    """Merge capture metadata into public seed objects.json (images stay private by default)."""
    from .config import SEED_PATH

    init_db()
    captures = list_captures(limit=5000)
    if not SEED_PATH.exists():
        seed = {
            "version": 1,
            "disclaimer": "Possible visual match data only — not legal ownership.",
            "objects": [],
        }
    else:
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    by_id = {o["id"]: o for o in seed.get("objects", [])}
    added = 0
    for cap in captures:
        oid = cap.get("linked_catalog_id") or cap["id"]
        geo = None
        if cap.get("lat") is not None and cap.get("lng") is not None:
            geo = {"lat": cap["lat"], "lng": cap["lng"]}
        images = []
        if include_private_image_urls and cap.get("image_relpath"):
            # Local-only path; not for public git demos
            images.append(
                {
                    "url": f"file://{(LOCAL_DIR / cap['image_relpath']).resolve()}",
                    "type": "historical",
                    "license": "restricted-research",
                    "attribution": cap.get("source_book") or "Bangdel research capture",
                    "visibility": "private",
                }
            )
        rec = {
            "id": oid,
            "titles": cap.get("titles") or [cap["title"]],
            "culture": cap.get("culture") or "Nepal",
            "period": cap.get("period"),
            "material": cap.get("material"),
            "dimensions": cap.get("dimensions"),
            "iconography_tags": cap.get("iconography_tags") or [],
            "status": cap.get("status") or "stolen_documented",
            "original_site": {
                "place": cap.get("place"),
                "tole": cap.get("tole"),
                "temple": cap.get("temple"),
                "geo": geo,
            },
            "current_location": None,
            "provenance_notes": " · ".join(
                filter(
                    None,
                    [
                        cap.get("provenance_notes"),
                        f"Bangdel page {cap['bangdel_page']}"
                        if cap.get("bangdel_page")
                        else None,
                        f"Plate {cap['bangdel_plate']}"
                        if cap.get("bangdel_plate")
                        else None,
                        cap.get("notes"),
                    ],
                )
            )
            or None,
            "theft_date": cap.get("theft_date"),
            "sources": [
                {
                    "label": "Bangdel research capture (local)",
                    "citation": cap.get("source_book")
                    or "Bangdel, Stolen Images of Nepal (1989).",
                }
            ],
            "images": images
            if include_private_image_urls
            else (by_id.get(oid, {}).get("images") or []),
            "match_links": by_id.get(oid, {}).get("match_links") or [],
        }
        # Preserve existing public museum images if merging
        if oid in by_id and by_id[oid].get("images") and not include_private_image_urls:
            rec["images"] = by_id[oid]["images"]
        by_id[oid] = rec
        added += 1

    seed["objects"] = list(by_id.values())
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(
        json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return added
