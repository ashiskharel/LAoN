#!/usr/bin/env python3
"""Export a YOLO .pt checkpoint to ONNX for CPU inference.

  pip install ultralytics
  python scripts/export_yolo_onnx.py --weights ml/weights/laon-artifact.pt

Writes ml/weights/laon-artifact.onnx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights",
        default=str(REPO / "ml" / "weights" / "laon-artifact.pt"),
    )
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    path = Path(args.weights)
    if not path.is_file():
        print(f"Weights not found: {path}")
        print("Train first (Colab notebook) or place best.pt at this path.")
        return 1
    try:
        from ultralytics import YOLO
    except ImportError:
        print("pip install ultralytics")
        return 1
    model = YOLO(str(path))
    out = model.export(format="onnx", imgsz=args.imgsz)
    out_path = Path(out)
    dest = REPO / "ml" / "weights" / "laon-artifact.onnx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if out_path.resolve() != dest.resolve():
        dest.write_bytes(out_path.read_bytes())
    print(f"Wrote {dest}")
    print("Restart API; GET /api/ml/status should show yolo.ready=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
