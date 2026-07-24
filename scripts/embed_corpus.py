#!/usr/bin/env python3
"""Build a simple embedding index from public (and optional private) images.

Default method: grayscale histogram + thumbnail features (no torch required).
Writes data/embeddings/index.npz
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "seed" / "objects.json"
OUT = REPO / "data" / "embeddings" / "index.npz"
CACHE = REPO / "data" / "cache"
PRIVATE = Path(
    __import__("os").environ.get("PRIVATE_CORPUS_PATH", REPO / "data" / "private")
)


def simple_vector(path_or_bytes, size: int = 32) -> np.ndarray:
    if isinstance(path_or_bytes, (str, Path)):
        img = Image.open(path_or_bytes)
    else:
        import io

        img = Image.open(io.BytesIO(path_or_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    hist, _ = np.histogram(arr, bins=32, range=(0.0, 1.0), density=True)
    vec = np.concatenate([arr.flatten(), hist.astype(np.float32)])
    return (vec / (np.linalg.norm(vec) + 1e-9)).astype(np.float32)


def fetch(url: str) -> bytes | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    path = CACHE / f"{key}.img"
    if path.exists():
        return path.read_bytes()
    try:
        with httpx.Client(timeout=45.0, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            path.write_bytes(r.content)
            return r.content
    except Exception as e:
        print(f"  ! fetch failed {url}: {e}")
        return None


def main() -> int:
    if not SEED.exists():
        print("No seed catalog found.")
        return 1
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    ids: list[str] = []
    urls: list[str] = []
    vectors: list[np.ndarray] = []

    for obj in seed.get("objects", []):
        oid = obj["id"]
        for img in obj.get("images") or []:
            if img.get("visibility", "public") != "public":
                continue
            url = img.get("url")
            if not url:
                continue
            raw = fetch(url)
            if not raw:
                continue
            try:
                v = simple_vector(raw)
            except Exception as e:
                print(f"  ! embed fail {oid}: {e}")
                continue
            ids.append(oid)
            urls.append(url)
            vectors.append(v)
            print(f"  + public {oid}")

    # Optional private local images: filename stem should map to object id prefix
    # e.g. data/private/met-12345.jpg or data/private/bangdel/seed-surya-saugal-type.jpg
    if PRIVATE.exists():
        for path in PRIVATE.rglob("*"):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            if path.name.startswith("."):
                continue
            # Map by parent folder or stem if matches an object id
            object_ids = {o["id"] for o in seed.get("objects", [])}
            stem = path.stem
            oid = stem if stem in object_ids else None
            if oid is None:
                # allow id as prefix: met-12345_plate1.jpg
                for candidate in object_ids:
                    if stem.startswith(candidate):
                        oid = candidate
                        break
            if oid is None:
                print(f"  ~ skip private (no object id match): {path.name}")
                continue
            try:
                v = simple_vector(path)
            except Exception as e:
                print(f"  ! private embed fail {path}: {e}")
                continue
            ids.append(oid)
            urls.append(f"file://{path.resolve()}")
            vectors.append(v)
            print(f"  + private {oid} <- {path.name}")

    if not vectors:
        print("No images embedded. Ingest museum images first.")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    mat = np.stack(vectors, axis=0)
    np.savez(
        OUT,
        ids=np.array(ids, dtype=object),
        image_urls=np.array(urls, dtype=object),
        vectors=mat,
        method=np.array("simple_hist"),
    )
    print(f"Wrote {OUT} with {len(ids)} vectors, dim={mat.shape[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
