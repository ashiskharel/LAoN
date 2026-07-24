from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
def health():
    return {"ok": True, "service": "laon-api", "version": "0.1.0"}


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
    return match_image(data, top_k=top_k)


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
