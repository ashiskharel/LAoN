from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


Status = Literal[
    "in_situ",
    "stolen_documented",
    "museum",
    "private",
    "repatriated",
    "unknown",
]


class Geo(BaseModel):
    lat: float
    lng: float


class OriginalSite(BaseModel):
    place: Optional[str] = None
    tole: Optional[str] = None
    temple: Optional[str] = None
    geo: Optional[Geo] = None


class CurrentLocation(BaseModel):
    institution: Optional[str] = None
    accession: Optional[str] = None
    url: Optional[str] = None
    country: Optional[str] = None


class Source(BaseModel):
    label: str
    url: Optional[str] = None
    citation: Optional[str] = None


class ObjectImage(BaseModel):
    url: str
    type: Literal["historical", "museum", "community", "empty_niche"]
    license: str
    attribution: Optional[str] = None
    source_url: Optional[str] = None
    visibility: Literal["public", "private"] = "public"
    photographer: Optional[str] = None


class CulturalObject(BaseModel):
    id: str
    titles: list[str]
    culture: Optional[str] = None
    period: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None
    iconography_tags: list[str] = Field(default_factory=list)
    status: Status
    original_site: Optional[OriginalSite] = None
    current_location: Optional[CurrentLocation] = None
    provenance_notes: Optional[str] = None
    theft_date: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)
    images: list[ObjectImage] = Field(default_factory=list)
    match_links: list[dict[str, Any]] = Field(default_factory=list)


class ObjectListResponse(BaseModel):
    disclaimer: str
    total: int
    objects: list[CulturalObject]


class MatchResult(BaseModel):
    object: CulturalObject
    score: float
    method: str
    matched_image_url: Optional[str] = None


class MatchResponse(BaseModel):
    disclaimer: str
    query_note: str
    results: list[MatchResult]


class ReportRequest(BaseModel):
    query_description: Optional[str] = None
    match_object_ids: list[str]
    notes: Optional[str] = None
    contact_email: Optional[str] = None


class ReportResponse(BaseModel):
    disclaimer: str
    generated_at: str
    report: dict[str, Any]
