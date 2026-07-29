"""Visual similarity: crop → embed → rank with confidence tiers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .config import DISCLAIMER
from .catalog import all_objects, get_object
from .embeddings import (
    confidence_for,
    embed_image,
    load_embedding_index,
    simple_image_vector,
)
from .models import CropInfo, MatchResult, MatchResponse
from .preprocess import crop_artifact


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


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


def _build_results(
    scored: list[tuple[float, str, str, str]],
    top_k: int,
) -> list[MatchResult]:
    """scored: (score, object_id, image_url, method) sorted desc."""
    results: list[MatchResult] = []
    seen: set[str] = set()
    for i, (score, oid, url, method) in enumerate(scored):
        if oid in seen:
            continue
        obj = get_object(oid)
        if not obj:
            continue
        seen.add(oid)
        next_score = None
        for j in range(i + 1, len(scored)):
            if scored[j][1] != oid:
                next_score = scored[j][0]
                break
        tier, note = confidence_for(score, method, next_score)
        results.append(
            MatchResult(
                object=obj,
                score=round(score, 4),
                method=method,
                matched_image_url=url,
                confidence=tier,
                confidence_note=note,
            )
        )
        if len(results) >= top_k:
            break
    return results


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
    crop_prefix = f"Preprocess crop={crop_res.method}. "

    index = load_embedding_index()
    results: list[MatchResult] = []
    query_note = ""

    if index is not None:
        method = index.get("method", "simple_hist")
        q_vec = embed_image(query_bytes, method)
        if q_vec.shape[0] == index["vectors"].shape[1]:
            scores = index["vectors"] @ q_vec
            order = np.argsort(-scores)
            scored: list[tuple[float, str, str, str]] = []
            for i in order:
                scored.append(
                    (
                        float(scores[i]),
                        index["ids"][i],
                        index["image_urls"][i],
                        method,
                    )
                )
            results = _build_results(scored, top_k)
            if method in ("openclip", "clip", "dinov2", "dino"):
                query_note = (
                    crop_prefix
                    + f"Ranking with {method} embeddings against precomputed index. "
                    "Confidence tiers are research aids only."
                )
            else:
                query_note = (
                    crop_prefix
                    + f"Ranking with {method} features against precomputed index. "
                    "Install sentence-transformers and re-run embed_corpus.py "
                    "--method openclip for stronger matching."
                )
            return MatchResponse(
                disclaimer=DISCLAIMER,
                query_note=query_note,
                results=results,
                crop=crop_info,
            )
        query_note = (
            crop_prefix
            + f"Index method={method} dim={index['vectors'].shape[1]} "
            f"but query dim={q_vec.shape[0]} — falling back to live simple match. "
            "Re-run scripts/embed_corpus.py with the same environment."
        )

    if not query_note:
        query_note = (
            crop_prefix
            + "No embedding index found. Live simple features on public images. "
            "Run: python scripts/embed_corpus.py"
        )
    else:
        query_note += " Using live simple features."

    q_vec = simple_image_vector(query_bytes)
    scored_live: list[tuple[float, str, str, str]] = []
    for obj in all_objects():
        for img in obj.images:
            if img.visibility != "public":
                continue
            raw = _load_url_bytes(img.url, cache)
            if not raw:
                continue
            try:
                v = simple_image_vector(raw)
                s = _cosine_sim(q_vec, v)
                scored_live.append((s, obj.id, img.url, "simple_hist_live"))
            except Exception:
                continue

    scored_live.sort(key=lambda x: -x[0])
    results = _build_results(scored_live, top_k)

    if not results:
        query_note += (
            " Catalog has few public images; expand via ingest scripts "
            "or Research export."
        )

    return MatchResponse(
        disclaimer=DISCLAIMER,
        query_note=query_note,
        results=results,
        crop=crop_info,
    )
