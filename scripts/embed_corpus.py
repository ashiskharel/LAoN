#!/usr/bin/env python3
"""Build embedding index from public (+ optional private) images.

Methods:
  simple   — grayscale hist (default, no torch)
  openclip — sentence-transformers clip-ViT-B-32 (optional)
  dinov2   — torch hub dinov2_vits14 (optional, heavier)

  python scripts/embed_corpus.py
  python scripts/embed_corpus.py --method openclip

Writes data/embeddings/index.npz
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(REPO / "services" / "api"))


def simple_vector(path_or_bytes, size: int = 32) -> np.ndarray:
    import io

    if isinstance(path_or_bytes, (str, Path)):
        img = Image.open(path_or_bytes)
    else:
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


def _probe_jpeg() -> bytes:
    from io import BytesIO

    buf = BytesIO()
    Image.new("RGB", (64, 64), (128, 128, 128)).save(buf, format="JPEG")
    return buf.getvalue()


def make_embedder(method: str):
    method = method.lower()
    if method in ("simple", "simple_hist"):
        return lambda b: simple_vector(b), "simple_hist"

    if method in ("openclip", "clip"):
        from app.embeddings import openclip_image_vector

        if openclip_image_vector(_probe_jpeg()) is None:
            raise SystemExit(
                "OpenCLIP not available. pip install sentence-transformers"
            )

        def _e(b: bytes) -> np.ndarray:
            v = openclip_image_vector(b)
            if v is None:
                raise RuntimeError("OpenCLIP embed failed")
            return v

        return _e, "openclip"

    if method in ("dinov2", "dino"):
        from app.embeddings import dinov2_image_vector

        if dinov2_image_vector(_probe_jpeg()) is None:
            raise SystemExit("DINOv2 not available. pip install torch torchvision")

        def _d(b: bytes) -> np.ndarray:
            v = dinov2_image_vector(b)
            if v is None:
                raise RuntimeError("DINOv2 embed failed")
            return v

        return _d, "dinov2"

    raise SystemExit(f"Unknown method: {method}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method",
        default="simple",
        choices=["simple", "simple_hist", "openclip", "clip", "dinov2", "dino"],
    )
    args = parser.parse_args()

    if not SEED.exists():
        print("No seed catalog found.")
        return 1

    embed_fn, method_name = make_embedder(args.method)
    print(f"Embedding method: {method_name}")

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
                v = embed_fn(raw)
            except Exception as e:
                print(f"  ! embed fail {oid}: {e}")
                continue
            ids.append(oid)
            urls.append(url)
            vectors.append(v)
            print(f"  + public {oid}")

    if PRIVATE.exists():
        object_ids = {o["id"] for o in seed.get("objects", [])}
        for path in PRIVATE.rglob("*"):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            if path.name.startswith("."):
                continue
            stem = path.stem
            oid = stem if stem in object_ids else None
            if oid is None:
                for candidate in object_ids:
                    if stem.startswith(candidate):
                        oid = candidate
                        break
            if oid is None:
                print(f"  ~ skip private (no object id match): {path.name}")
                continue
            try:
                v = embed_fn(path.read_bytes())
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
        method=np.array(method_name),
    )
    print(f"Wrote {OUT} with {len(ids)} vectors, dim={mat.shape[1]}, method={method_name}")
    return 0


if __name__ == "__main__":
    # Fix broken warm-up in openclip branch — use clean path
    sys.exit(main())
