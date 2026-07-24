from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import CORS_ORIGINS, DISCLAIMER
from .catalog import get_object, load_geojson, reload_catalog, search_objects
from .models import (
    MatchResponse,
    ObjectListResponse,
    ReportRequest,
    ReportResponse,
    CulturalObject,
)
from .vision import match_image
from . import research_db

app = FastAPI(
    title="LAoN API",
    description=(
        "Lost Ancient Arts of Nepal — catalog and visual match API. "
        + DISCLAIMER
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local research SQLite (Bangdel captures, etc.)
research_db.init_db()


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "laon-api",
        "version": "0.1.0",
        "research_db": str(research_db.DB_PATH),
    }


@app.get("/api/disclaimer")
def disclaimer():
    return {"disclaimer": DISCLAIMER}


@app.get("/api/objects", response_model=ObjectListResponse)
def list_objects(
    q: Optional[str] = Query(None, description="Free-text search"),
    status: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    place: Optional[str] = Query(None),
):
    objects = search_objects(q=q, status=status, tag=tag, place=place)
    return ObjectListResponse(
        disclaimer=DISCLAIMER,
        total=len(objects),
        objects=objects,
    )


@app.get("/api/objects/{object_id}", response_model=CulturalObject)
def object_detail(object_id: str):
    obj = get_object(object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


@app.get("/api/geo")
def geo():
    return load_geojson()


@app.post("/api/match", response_model=MatchResponse)
async def match(
    file: UploadFile = File(...),
    top_k: int = Query(8, ge=1, le=30),
    crop: bool = Query(
        True,
        description="ML-0: crop/focus the main artifact before matching (recommended).",
    ),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        # Allow octet-stream from some mobile clients
        if file.content_type not in (None, "application/octet-stream"):
            raise HTTPException(
                status_code=400,
                detail="Upload an image file (image/*).",
            )
    data = await file.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 12MB).")
    if len(data) < 32:
        raise HTTPException(status_code=400, detail="Empty or invalid image.")
    return match_image(data, top_k=top_k, crop=crop)


@app.post("/api/report", response_model=ReportResponse)
def build_report(body: ReportRequest):
    matches = []
    for oid in body.match_object_ids:
        obj = get_object(oid)
        if obj:
            matches.append(obj.model_dump())
    report = {
        "title": "LAoN possible match evidence package",
        "disclaimer": DISCLAIMER,
        "query_description": body.query_description,
        "notes": body.notes,
        "contact_email": body.contact_email,
        "matches": matches,
        "guidance": [
            "This package is not a legal claim.",
            "Verify iconography, measurements, and damage marks with specialists.",
            "Only authorized government channels can pursue formal restitution.",
            "Share responsibly; avoid public accusations based on score alone.",
        ],
    }
    return ReportResponse(
        disclaimer=DISCLAIMER,
        generated_at=datetime.now(timezone.utc).isoformat(),
        report=report,
    )


@app.post("/api/admin/reload")
def admin_reload():
    """Reload seed JSON from disk (local dev helper)."""
    reload_catalog()
    return {"ok": True, "total": len(search_objects())}


# —— Local research capture (Bangdel plates, field notes) ——


@app.get("/api/research/captures")
def research_list(
    q: Optional[str] = None,
    place: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
):
    items = research_db.list_captures(q=q, place=place, limit=limit)
    return {
        "disclaimer": DISCLAIMER,
        "note": "Local research DB only. Bangdel plate images stay private on this machine.",
        "total": len(items),
        "db_path": str(research_db.DB_PATH),
        "captures": items,
    }


@app.get("/api/research/captures/{capture_id}")
def research_get(capture_id: str):
    cap = research_db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")
    return cap


@app.get("/api/research/captures/{capture_id}/image")
def research_image(capture_id: str):
    path = research_db.image_path_for(capture_id)
    if not path:
        raise HTTPException(status_code=404, detail="Image not found")
    media = "image/jpeg"
    if path.suffix.lower() == ".png":
        media = "image/png"
    elif path.suffix.lower() == ".webp":
        media = "image/webp"
    return FileResponse(path, media_type=media)


@app.post("/api/research/captures")
async def research_create(
    title: str = Form(...),
    file: Optional[UploadFile] = File(None),
    culture: str = Form("Nepal"),
    period: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    iconography_tags: Optional[str] = Form(
        None, description="Comma-separated tags, e.g. uma-mahesvara,saiva"
    ),
    status: str = Form("stolen_documented"),
    place: Optional[str] = Form(None),
    tole: Optional[str] = Form(None),
    temple: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    theft_date: Optional[str] = Form(None),
    bangdel_page: Optional[str] = Form(None),
    bangdel_plate: Optional[str] = Form(None),
    source_book: str = Form(
        "Bangdel, Lain Singh. Stolen Images of Nepal. Royal Nepal Academy, 1989."
    ),
    provenance_notes: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    linked_catalog_id: Optional[str] = Form(
        None, description="Optional existing catalog id to link for matching"
    ),
    capture_id: Optional[str] = Form(None),
):
    image_bytes = None
    image_filename = None
    if file is not None and file.filename:
        image_bytes = await file.read()
        image_filename = file.filename
        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 20MB).")
    tags = [
        t.strip().lower().replace(" ", "-")
        for t in (iconography_tags or "").split(",")
        if t.strip()
    ]
    if not title.strip():
        raise HTTPException(status_code=400, detail="Title is required.")
    cap = research_db.save_capture(
        title=title.strip(),
        image_bytes=image_bytes,
        image_filename=image_filename,
        culture=culture,
        period=period or None,
        material=material or None,
        dimensions=dimensions or None,
        iconography_tags=tags,
        status=status or "stolen_documented",
        place=place or None,
        tole=tole or None,
        temple=temple or None,
        lat=lat,
        lng=lng,
        theft_date=theft_date or None,
        bangdel_page=bangdel_page or None,
        bangdel_plate=bangdel_plate or None,
        source_book=source_book,
        provenance_notes=provenance_notes or None,
        notes=notes or None,
        capture_id=capture_id or None,
        linked_catalog_id=linked_catalog_id or None,
    )
    return {
        "ok": True,
        "capture": cap,
        "image_url": f"/api/research/captures/{cap['id']}/image"
        if cap.get("image_relpath")
        else None,
    }


@app.delete("/api/research/captures/{capture_id}")
def research_delete(capture_id: str):
    if not research_db.delete_capture(capture_id):
        raise HTTPException(status_code=404, detail="Capture not found")
    return {"ok": True}


@app.post("/api/research/export")
def research_export(
    sync_seed: bool = Query(
        True,
        description="Merge capture metadata into data/seed/objects.json (no public plate images)",
    ),
    copy_private: bool = Query(
        True,
        description="Copy images into data/private/bangdel for embed_corpus.py",
    ),
):
    """Prepare local captures for matching: private images + public metadata."""
    n_img = research_db.export_private_corpus_links() if copy_private else 0
    n_meta = research_db.sync_metadata_to_seed(include_private_image_urls=False) if sync_seed else 0
    if sync_seed:
        reload_catalog()
    return {
        "ok": True,
        "images_copied_to_private": n_img,
        "metadata_synced_to_seed": n_meta,
        "next": "Run: python scripts/embed_corpus.py  then POST /api/admin/reload",
        "db_path": str(research_db.DB_PATH),
    }
