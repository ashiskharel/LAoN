"""Visual similarity: optional precomputed embeddings + lightweight fallback."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from .config import EMBEDDINGS_PATH, DISCLAIMER
from .catalog import all_objects, get_object
from .models import CropInfo, MatchResult, MatchResponse
from .preprocess import crop_artifact


def _load_embedding_index() -> Optional[dict]:
    if not EMBEDDINGS_PATH.exists():
        return None
    data = np.load(EMBEDDINGS_PATH, allow_pickle=True)
    return {
        "ids": data["ids"].tolist(),
        "vectors": data["vectors"].astype(np.float32),
        "image_urls": data["image_urls"].tolist(),
        "method": str(data["method"]) if "method" in data else "embedding",
    }


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def _simple_image_vector(image_bytes: bytes, size: int = 32) -> np.ndarray:
    """Grayscale thumbnail histogram — weak but dependency-free fallback."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    # Flatten + coarse histogram for a bit more invariance
    hist, _ = np.histogram(arr, bins=32, range=(0.0, 1.0), density=True)
    vec = np.concatenate([arr.flatten(), hist.astype(np.float32)])
    vec = vec / (np.linalg.norm(vec) + 1e-9)
    return vec.astype(np.float32)


def _load_url_bytes(url: str, cache_dir: Path) -> Optional[bytes]:
    import hashlib
    import httpx

    if url.startswith("file://"):
        path = Path(url.removeprefix("file://"))
        if path.exists():
            return path.read_bytes()
        return None

    if url.startswith("/") or (len(url) > 2 and url[1] == ":"):
        path = Path(url)
        if path.exists():
            return path.read_bytes()
        return None

    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    cache_path = cache_dir / f"{key}.img"
    if cache_path.exists():
        return cache_path.read_bytes()
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            cache_path.write_bytes(r.content)
            return r.content
    except Exception:
        return None


def match_image(
    image_bytes: bytes,
    top_k: int = 8,
    cache_dir: Optional[Path] = None,
    *,
    crop: bool = True,
) -> MatchResponse:
    from .config import CACHE_DIR

    cache = cache_dir or CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)

    # ML-0: crop/focus artifact before embedding
    crop_res = crop_artifact(image_bytes, enabled=crop)
    query_bytes = crop_res.image_bytes if crop else image_bytes
    crop_info = CropInfo(
        method=crop_res.method,
        bbox=list(crop_res.bbox),
        original_size=list(crop_res.original_size),
        cropped_size=list(crop_res.cropped_size),
        preview_jpeg_b64=crop_res.preview_jpeg_b64,
        note=crop_res.note,
    )

    index = _load_embedding_index()
    query_note = ""
    results: list[MatchResult] = []
    crop_prefix = f"Preprocess crop={crop_res.method}. "

    if index is not None:
        # Prefer precomputed vectors if query embedding method matches simple fallback
        # For OpenCLIP index, operators re-embed queries with the same model offline.
        # Here we still support simple vectors stored by embed_corpus.py fallback mode.
        method = index.get("method", "embedding")
        if method in ("simple_hist", "embedding", "openclip"):
            if method == "openclip":
                query_note = (
                    crop_prefix
                    + "Index was built with OpenCLIP; query uses simple features unless "
                    "you re-run embed tooling for live OpenCLIP. Ranking may be weak."
                )
                q_vec = _simple_image_vector(query_bytes)
            else:
                q_vec = _simple_image_vector(query_bytes)
                query_note = (
                    crop_prefix
                    + f"Ranking with {method} features against precomputed index."
                )

            # If dimensions mismatch (OpenCLIP vs simple), fall through to live simple
            if q_vec.shape[0] == index["vectors"].shape[1]:
                scores = index["vectors"] @ q_vec
                order = np.argsort(-scores)[: top_k * 3]
                seen: set[str] = set()
                for i in order:
                    oid = index["ids"][i]
                    if oid in seen:
                        continue
                    obj = get_object(oid)
                    if not obj:
                        continue
                    seen.add(oid)
                    results.append(
                        MatchResult(
                            object=obj,
                            score=round(float(scores[i]), 4),
                            method=method,
                            matched_image_url=index["image_urls"][i],
                        )
                    )
                    if len(results) >= top_k:
                        break
                return MatchResponse(
                    disclaimer=DISCLAIMER,
                    query_note=query_note
                    or (crop_prefix + "Visual match against embedding index."),
                    results=results,
                    crop=crop_info,
                )

    # Live simple similarity against public images in catalog
    query_note = (
        crop_prefix
        + "No compatible embedding index found (or dimension mismatch). "
        "Using live simple grayscale features on public catalog images. "
        "Run scripts/embed_corpus.py after adding images for better results."
    )
    q_vec = _simple_image_vector(query_bytes)
    scored: list[tuple[float, str, str]] = []

    for obj in all_objects():
        for img in obj.images:
            if img.visibility != "public":
                continue
            raw = _load_url_bytes(img.url, cache)
            if not raw:
                continue
            try:
                v = _simple_image_vector(raw)
                s = _cosine_sim(q_vec, v)
                scored.append((s, obj.id, img.url))
            except Exception:
                continue

    scored.sort(key=lambda x: -x[0])
    seen_ids: set[str] = set()
    for score, oid, url in scored:
        if oid in seen_ids:
            continue
        obj = get_object(oid)
        if not obj:
            continue
        seen_ids.add(oid)
        results.append(
            MatchResult(
                object=obj,
                score=round(score, 4),
                method="simple_hist_live",
                matched_image_url=url,
            )
        )
        if len(results) >= top_k:
            break

    if not results:
        # Still return text-ish empty with objects that have no images
        query_note += (
            " Catalog currently has few public images; expand seed via "
            "scripts/ingest_met.py and scripts/ingest_cleveland.py."
        )

    return MatchResponse(
        disclaimer=DISCLAIMER,
        query_note=query_note,
        results=results,
        crop=crop_info,
    )
