"""Artifact crop / segmentation preprocessing.

Cost-effective stack for a social project (priority order):
1. ML-1 YOLO weights in ml/weights/ (optional ultralytics or onnxruntime)
2. rembg U2Net if installed
3. Edge-saliency / center fallback (always available)

Does not identify deities — only focuses the frame on the main object.
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass
class CropResult:
    image_bytes: bytes
    method: str
    bbox: tuple[int, int, int, int]  # x0, y0, x1, y1 in original pixels
    original_size: tuple[int, int]  # w, h
    cropped_size: tuple[int, int]
    preview_jpeg_b64: Optional[str] = None
    note: str = ""


def _encode_jpeg_b64(img: Image.Image, quality: int = 82) -> str:
    buf = io.BytesIO()
    rgb = img.convert("RGB")
    rgb.save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _to_jpeg_bytes(img: Image.Image, quality: int = 90) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _load_image(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def _bbox_from_mask(mask: np.ndarray, pad_frac: float = 0.04) -> Optional[tuple[int, int, int, int]]:
    """mask: HxW bool or 0/1."""
    ys, xs = np.where(mask > 0)
    if len(xs) < 20:
        return None
    h, w = mask.shape
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    # Reject tiny / huge degenerate boxes
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    if bw * bh < 0.02 * w * h:
        return None
    if bw * bh > 0.98 * w * h:
        return None
    pad_x = int(pad_frac * w)
    pad_y = int(pad_frac * h)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w - 1, x1 + pad_x)
    y1 = min(h - 1, y1 + pad_y)
    return x0, y0, x1, y1


def crop_with_rembg(image_bytes: bytes) -> Optional[CropResult]:
    """Optional high-quality background removal (needs rembg + onnxruntime)."""
    if os.environ.get("LAON_DISABLE_REMBG", "").lower() in {"1", "true", "yes"}:
        return None
    try:
        from rembg import remove  # type: ignore
    except Exception:
        return None

    try:
        img = _load_image(image_bytes)
        # Downscale for speed on CPU
        max_side = 1024
        scale = min(1.0, max_side / max(img.size))
        work = img
        if scale < 1.0:
            work = img.resize(
                (int(img.width * scale), int(img.height * scale)),
                Image.Resampling.LANCZOS,
            )
        work_bytes = _to_jpeg_bytes(work, quality=92)
        out = remove(work_bytes)
        rgba = Image.open(io.BytesIO(out)).convert("RGBA")
        alpha = np.asarray(rgba.split()[-1])
        mask = alpha > 32
        bbox_s = _bbox_from_mask(mask)
        if not bbox_s:
            return None
        # Map bbox back to original coords
        if scale < 1.0:
            x0, y0, x1, y1 = bbox_s
            x0 = int(x0 / scale)
            y0 = int(y0 / scale)
            x1 = int(x1 / scale)
            y1 = int(y1 / scale)
            bbox = (
                max(0, x0),
                max(0, y0),
                min(img.width - 1, x1),
                min(img.height - 1, y1),
            )
        else:
            bbox = bbox_s
        x0, y0, x1, y1 = bbox
        cropped = img.crop((x0, y0, x1 + 1, y1 + 1))
        jpeg = _to_jpeg_bytes(cropped)
        return CropResult(
            image_bytes=jpeg,
            method="rembg",
            bbox=bbox,
            original_size=(img.width, img.height),
            cropped_size=cropped.size,
            preview_jpeg_b64=_encode_jpeg_b64(cropped),
            note="Foreground segmented with rembg (U2Net). Optional dependency.",
        )
    except Exception:
        return None


def crop_with_edge_saliency(image_bytes: bytes) -> CropResult:
    """Dependency-free crop: edge energy + center prior → bounding box."""
    img = _load_image(image_bytes)
    # Work at moderate resolution
    max_side = 640
    scale = min(1.0, max_side / max(img.size))
    small = img
    if scale < 1.0:
        small = img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
            Image.Resampling.LANCZOS,
        )

    gray = small.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(edges, dtype=np.float32)
    # Soft threshold
    thr = max(12.0, float(np.percentile(arr, 70)))
    mask = arr >= thr

    # Suppress outer border a bit (often frames / UI chrome)
    h, w = mask.shape
    border = max(2, int(0.03 * min(h, w)))
    mask[:border, :] = False
    mask[-border:, :] = False
    mask[:, :border] = False
    mask[:, -border:] = False

    # Center prior: boost middle region
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt(((yy - cy) / (h / 2.0 + 1e-6)) ** 2 + ((xx - cx) / (w / 2.0 + 1e-6)) ** 2)
    center_weight = np.clip(1.2 - 0.7 * dist, 0.2, 1.2)
    score = arr * center_weight
    thr2 = max(thr, float(np.percentile(score, 75)))
    mask2 = score >= thr2

    bbox_s = _bbox_from_mask(mask2.astype(np.uint8))
    if not bbox_s:
        # Fallback: central 70% crop
        mw, mh = small.size
        x0 = int(0.15 * mw)
        y0 = int(0.10 * mh)
        x1 = int(0.85 * mw) - 1
        y1 = int(0.90 * mh) - 1
        bbox_s = (x0, y0, x1, y1)
        method_note = "Central crop fallback (weak edges)."
        method = "center_fallback"
    else:
        method_note = "Edge-saliency crop (Pillow + NumPy, no GPU)."
        method = "edge_saliency"

    if scale < 1.0:
        x0, y0, x1, y1 = bbox_s
        bbox = (
            int(x0 / scale),
            int(y0 / scale),
            int(x1 / scale),
            int(y1 / scale),
        )
        bbox = (
            max(0, bbox[0]),
            max(0, bbox[1]),
            min(img.width - 1, bbox[2]),
            min(img.height - 1, bbox[3]),
        )
    else:
        bbox = bbox_s

    x0, y0, x1, y1 = bbox
    cropped = img.crop((x0, y0, x1 + 1, y1 + 1))
    jpeg = _to_jpeg_bytes(cropped)
    return CropResult(
        image_bytes=jpeg,
        method=method,
        bbox=bbox,
        original_size=(img.width, img.height),
        cropped_size=cropped.size,
        preview_jpeg_b64=_encode_jpeg_b64(cropped),
        note=method_note,
    )


def crop_with_yolo(image_bytes: bytes) -> Optional[CropResult]:
    """ML-1: crop using local YOLO weights if present."""
    try:
        from .yolo_crop import detect_artifact_bbox
    except Exception:
        return None
    try:
        hit = detect_artifact_bbox(image_bytes)
    except Exception:
        return None
    if not hit:
        return None
    bbox, method = hit
    img = _load_image(image_bytes)
    x0, y0, x1, y1 = bbox
    cropped = img.crop((x0, y0, x1 + 1, y1 + 1))
    return CropResult(
        image_bytes=_to_jpeg_bytes(cropped),
        method=method,
        bbox=bbox,
        original_size=(img.width, img.height),
        cropped_size=cropped.size,
        preview_jpeg_b64=_encode_jpeg_b64(cropped),
        note="Cropped with community-trained / local YOLO artifact detector.",
    )


def crop_artifact(
    image_bytes: bytes,
    *,
    enabled: bool = True,
    prefer_rembg: bool = True,
    prefer_yolo: bool = True,
) -> CropResult:
    """Return best available crop. If disabled, returns full image as pass-through."""
    img = _load_image(image_bytes)
    if not enabled:
        jpeg = _to_jpeg_bytes(img)
        return CropResult(
            image_bytes=jpeg,
            method="none",
            bbox=(0, 0, img.width - 1, img.height - 1),
            original_size=(img.width, img.height),
            cropped_size=img.size,
            preview_jpeg_b64=_encode_jpeg_b64(img),
            note="Crop disabled.",
        )

    if prefer_yolo:
        yolo = crop_with_yolo(image_bytes)
        if yolo is not None:
            return yolo

    if prefer_rembg:
        rem = crop_with_rembg(image_bytes)
        if rem is not None:
            return rem

    return crop_with_edge_saliency(image_bytes)
