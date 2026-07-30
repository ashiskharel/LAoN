"""ML-1: optional YOLO detect/segment crop using local weights.

Looks for (first match wins):
  LAON_YOLO_WEIGHTS env path
  ml/weights/laon-artifact.onnx
  ml/weights/laon-artifact.pt

Runtime options (any one is enough):
  - ultralytics (easiest for .pt / .onnx)
  - onnxruntime only for detect ONNX (no ultralytics)

If weights or deps missing, returns None so preprocess can fall back to rembg/edge.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .config import REPO_ROOT

WEIGHT_CANDIDATES = [
    os.environ.get("LAON_YOLO_WEIGHTS", "").strip(),
    str(REPO_ROOT / "ml" / "weights" / "laon-artifact.onnx"),
    str(REPO_ROOT / "ml" / "weights" / "laon-artifact.pt"),
    str(REPO_ROOT / "ml" / "weights" / "best.onnx"),
    str(REPO_ROOT / "ml" / "weights" / "best.pt"),
]


def resolve_weights() -> Optional[Path]:
    for c in WEIGHT_CANDIDATES:
        if not c:
            continue
        p = Path(c)
        if p.is_file():
            return p
    return None


def yolo_status() -> dict:
    path = resolve_weights()
    ultra = False
    ort = False
    try:
        import ultralytics  # noqa: F401

        ultra = True
    except Exception:
        pass
    try:
        import onnxruntime  # noqa: F401

        ort = True
    except Exception:
        pass
    return {
        "weights_path": str(path) if path else None,
        "ultralytics_available": ultra,
        "onnxruntime_available": ort,
        "ready": bool(path) and (ultra or (ort and path and path.suffix.lower() == ".onnx")),
    }


@lru_cache(maxsize=1)
def _ultra_model(path_str: str):
    from ultralytics import YOLO

    return YOLO(path_str)


def _crop_with_ultralytics(
    image_bytes: bytes, weights: Path
) -> Optional[tuple[tuple[int, int, int, int], str]]:
    import io

    model = _ultra_model(str(weights))
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # conf modest — gallery photos are noisy
    results = model.predict(img, conf=0.25, verbose=False)
    if not results:
        return None
    r0 = results[0]
    boxes = getattr(r0, "boxes", None)
    if boxes is None or len(boxes) == 0:
        # try masks xyxy if segment model
        if getattr(r0, "masks", None) is not None and r0.masks is not None:
            # use box from masks
            if hasattr(r0.masks, "xy") and len(r0.masks.xy) > 0:
                # fall through — ultralytics still fills boxes for seg models usually
                pass
        if boxes is None or len(boxes) == 0:
            return None

    # pick largest box by area
    xyxy = boxes.xyxy.cpu().numpy()
    areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
    i = int(np.argmax(areas))
    x0, y0, x1, y1 = [int(v) for v in xyxy[i]]
    w, h = img.size
    # pad 4%
    pad_x = int(0.04 * w)
    pad_y = int(0.04 * h)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w - 1, x1 + pad_x)
    y1 = min(h - 1, y1 + pad_y)
    # reject tiny
    if (x1 - x0) * (y1 - y0) < 0.02 * w * h:
        return None
    return (x0, y0, x1, y1), f"yolo_ultralytics:{weights.name}"


def _letterbox(im: np.ndarray, new_shape: int = 640):
    """Resize + pad to square, return image, ratio, (dw, dh)."""
    h, w = im.shape[:2]
    r = min(new_shape / h, new_shape / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    import cv2

    resized = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_shape, new_shape, 3), 114, dtype=np.uint8)
    dw, dh = (new_shape - nw) // 2, (new_shape - nh) // 2
    canvas[dh : dh + nh, dw : dw + nw] = resized
    return canvas, r, dw, dh


def _crop_with_onnxruntime(
    image_bytes: bytes, weights: Path
) -> Optional[tuple[tuple[int, int, int, int], str]]:
    """Minimal YOLOv8/v11 detect ONNX decode (no segment masks)."""
    import io

    try:
        import onnxruntime as ort
    except Exception:
        return None

    # Prefer OpenCV for letterbox; fall back to PIL if cv2 missing
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.asarray(img)[:, :, ::-1].copy()  # BGR for cv2 path
    try:
        import cv2

        lb, ratio, dw, dh = _letterbox(arr, 640)
        blob = lb[:, :, ::-1].transpose(2, 0, 1)  # RGB CHW
    except Exception:
        # pure numpy/PIL letterbox
        h, w = arr.shape[:2]
        r = min(640 / h, 640 / w)
        nh, nw = int(round(h * r)), int(round(w * r))
        resized = np.array(img.resize((nw, nh), Image.Resampling.BILINEAR))
        canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
        dw, dh = (640 - nw) // 2, (640 - nh) // 2
        canvas[dh : dh + nh, dw : dw + nw] = resized
        ratio = r
        blob = canvas.transpose(2, 0, 1)

    blob = blob.astype(np.float32) / 255.0
    blob = np.expand_dims(blob, 0)

    sess = ort.InferenceSession(str(weights), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0].name
    out = sess.run(None, {inp: blob})[0]
    # shapes: (1, 4+nc, N) or (1, N, 4+nc)
    out = np.squeeze(out)
    if out.ndim != 2:
        return None
    if out.shape[0] < out.shape[1] and out.shape[0] <= 84 + 10:
        # (4+nc, N)
        pred = out.T
    else:
        pred = out

    if pred.shape[1] < 5:
        return None
    boxes = pred[:, :4]
    # objectness * class or just max class score
    if pred.shape[1] == 5:
        scores = pred[:, 4]
    else:
        scores = pred[:, 4:].max(axis=1)

    # xywh → xyxy in letterbox space (ultralytics export usually xywh)
    # Heuristic: if mean of coords suggests xyxy already (x2>x1 large)
    xyxy = np.zeros_like(boxes)
    # assume center xywh
    xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
    xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
    xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
    xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2

    mask = scores >= 0.25
    if not np.any(mask):
        return None
    xyxy = xyxy[mask]
    scores = scores[mask]
    # largest by area after mapping back
    areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
    i = int(np.argmax(areas))
    x0, y0, x1, y1 = xyxy[i]

    # undo letterbox
    x0 = (x0 - dw) / ratio
    x1 = (x1 - dw) / ratio
    y0 = (y0 - dh) / ratio
    y1 = (y1 - dh) / ratio

    w, h = img.size
    x0 = int(max(0, min(w - 1, x0)))
    x1 = int(max(0, min(w - 1, x1)))
    y0 = int(max(0, min(h - 1, y0)))
    y1 = int(max(0, min(h - 1, y1)))
    if x1 <= x0 or y1 <= y0:
        return None
    if (x1 - x0) * (y1 - y0) < 0.02 * w * h:
        return None
    pad_x = int(0.04 * w)
    pad_y = int(0.04 * h)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w - 1, x1 + pad_x)
    y1 = min(h - 1, y1 + pad_y)
    return (x0, y0, x1, y1), f"yolo_onnxruntime:{weights.name}"


def detect_artifact_bbox(
    image_bytes: bytes,
) -> Optional[tuple[tuple[int, int, int, int], str]]:
    if os.environ.get("LAON_DISABLE_YOLO", "").lower() in {"1", "true", "yes"}:
        return None
    weights = resolve_weights()
    if not weights:
        return None

    # Prefer ultralytics when installed
    try:
        import ultralytics  # noqa: F401

        return _crop_with_ultralytics(image_bytes, weights)
    except Exception:
        pass

    if weights.suffix.lower() == ".onnx":
        try:
            return _crop_with_onnxruntime(image_bytes, weights)
        except Exception:
            return None
    return None
