#!/usr/bin/env python3
"""Bootstrap a starter YOLO dataset from public seed museum images.

Creates weak full-frame (or edge-saliency) boxes as class 0 `artifact`.
Use this only as a starting point — replace with real human boxes ASAP.

  python scripts/bootstrap_yolo_dataset.py
  python scripts/bootstrap_yolo_dataset.py --limit 40 --val-ratio 0.2

Then train on Colab (see ml/notebooks/train_yolo_colab.ipynb).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "seed" / "objects.json"
CACHE = REPO / "data" / "cache"
OUT = REPO / "ml" / "datasets" / "artifact"
sys.path.insert(0, str(REPO / "services" / "api"))


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
        print(f"  ! {url}: {e}")
        return None


def yolo_line_from_bbox(x0, y0, x1, y1, w, h) -> str:
    cx = ((x0 + x1) / 2) / w
    cy = ((y0 + y1) / 2) / h
    bw = (x1 - x0) / w
    bh = (y1 - y0) / h
    return f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument(
        "--mode",
        choices=["center", "edge"],
        default="edge",
        help="center=70% center box; edge=edge-saliency crop as box",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    if not SEED.exists():
        print("No seed catalog")
        return 1
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    items = []
    for obj in seed.get("objects", []):
        for img in obj.get("images") or []:
            if img.get("visibility", "public") != "public":
                continue
            url = img.get("url")
            if url:
                items.append((obj["id"], url))
    random.shuffle(items)
    items = items[: args.limit]
    if not items:
        print("No public images in seed. Run ingest_cleveland.py first.")
        return 1

    for split in ("train", "val"):
        (OUT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT / "labels" / split).mkdir(parents=True, exist_ok=True)

    n_train = 0
    n_val = 0
    for i, (oid, url) in enumerate(items):
        raw = fetch(url)
        if not raw:
            continue
        try:
            img = ImageOps.exif_transpose(Image.open(__import__("io").BytesIO(raw))).convert(
                "RGB"
            )
        except Exception as e:
            print(f"  ! open {oid}: {e}")
            continue
        w, h = img.size
        if args.mode == "edge":
            from app.preprocess import crop_with_edge_saliency
            import io

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            crop = crop_with_edge_saliency(buf.getvalue())
            x0, y0, x1, y1 = crop.bbox
        else:
            x0, y0 = int(0.15 * w), int(0.10 * h)
            x1, y1 = int(0.85 * w) - 1, int(0.90 * h) - 1

        split = "val" if random.random() < args.val_ratio else "train"
        stem = f"{oid}_{i}"
        img_path = OUT / "images" / split / f"{stem}.jpg"
        lbl_path = OUT / "labels" / split / f"{stem}.txt"
        img.save(img_path, format="JPEG", quality=92)
        lbl_path.write_text(yolo_line_from_bbox(x0, y0, x1, y1, w, h) + "\n", encoding="utf-8")
        if split == "train":
            n_train += 1
        else:
            n_val += 1
        print(f"  + {split} {stem}")

    print(f"Done. train={n_train} val={n_val} under {OUT}")
    print("Next: zip ml/datasets/artifact and train in Colab, or:")
    print("  yolo detect train data=ml/configs/laon-artifact.yaml model=yolo11n.pt epochs=50")
    print("Copy best.pt → ml/weights/laon-artifact.pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
