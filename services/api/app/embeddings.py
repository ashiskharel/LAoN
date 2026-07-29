"""Image embedding helpers for visual match.

Default: simple grayscale histogram (no extra deps).
Optional: OpenCLIP via sentence-transformers when installed
  pip install sentence-transformers  (pulls torch — use Colab/GPU if slow)

Index file: data/embeddings/index.npz with keys ids, vectors, image_urls, method
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from .config import EMBEDDINGS_PATH


def simple_image_vector(image_bytes: bytes, size: int = 32) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    hist, _ = np.histogram(arr, bins=32, range=(0.0, 1.0), density=True)
    vec = np.concatenate([arr.flatten(), hist.astype(np.float32)])
    return (vec / (np.linalg.norm(vec) + 1e-9)).astype(np.float32)


@lru_cache(maxsize=1)
def _openclip_model():
    try:
        from sentence_transformers import SentenceTransformer

        # CLIP multimodal; encode images with model.encode
        return SentenceTransformer("clip-ViT-B-32")
    except Exception:
        return None


def openclip_image_vector(image_bytes: bytes) -> Optional[np.ndarray]:
    model = _openclip_model()
    if model is None:
        return None
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("RGB")
    emb = model.encode(img, convert_to_numpy=True)
    vec = np.asarray(emb, dtype=np.float32).flatten()
    return (vec / (np.linalg.norm(vec) + 1e-9)).astype(np.float32)


@lru_cache(maxsize=1)
def _dinov2_model():
    """Optional torch hub DINOv2 small — heavy; only if torch available."""
    try:
        import torch
        from torchvision import transforms

        model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14")
        model.eval()
        tfm = transforms.Compose(
            [
                transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)
                ),
            ]
        )
        return model, tfm, torch
    except Exception:
        return None


def dinov2_image_vector(image_bytes: bytes) -> Optional[np.ndarray]:
    loaded = _dinov2_model()
    if loaded is None:
        return None
    model, tfm, torch = loaded
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("RGB")
    with torch.no_grad():
        t = tfm(img).unsqueeze(0)
        feat = model(t)
        vec = feat.squeeze(0).cpu().numpy().astype(np.float32)
    return (vec / (np.linalg.norm(vec) + 1e-9)).astype(np.float32)


def embed_image(image_bytes: bytes, method: str) -> np.ndarray:
    """Embed with requested method; fall back to simple if optional stack missing."""
    m = (method or "simple_hist").lower()
    if m in ("openclip", "clip", "clip-vit-b-32"):
        v = openclip_image_vector(image_bytes)
        if v is not None:
            return v
    if m in ("dinov2", "dino"):
        v = dinov2_image_vector(image_bytes)
        if v is not None:
            return v
    return simple_image_vector(image_bytes)


def load_embedding_index(path: Optional[Path] = None) -> Optional[dict]:
    p = path or EMBEDDINGS_PATH
    if not p.exists():
        return None
    data = np.load(p, allow_pickle=True)
    method = data["method"]
    if isinstance(method, np.ndarray):
        method = str(method.item() if method.shape == () else method[0])
    else:
        method = str(method)
    return {
        "ids": data["ids"].tolist(),
        "vectors": data["vectors"].astype(np.float32),
        "image_urls": data["image_urls"].tolist(),
        "method": method,
    }


def confidence_for(
    score: float,
    method: str,
    next_score: Optional[float] = None,
) -> tuple[str, str]:
    """Return (tier, human note). Tiers: high | medium | low | uncertain."""
    gap = (score - next_score) if next_score is not None else None
    m = (method or "").lower()

    if "simple" in m:
        # Simple hist over-scores; be conservative
        if score >= 0.985 and (gap is None or gap >= 0.01):
            return (
                "high",
                "Strong similarity on basic features — still verify by eye.",
            )
        if score >= 0.96:
            return (
                "medium",
                "Moderate similarity; compare details (hands, base, damage).",
            )
        if score >= 0.92:
            return (
                "low",
                "Weak signal only. Treat as a lead, not a match.",
            )
        return (
            "uncertain",
            "Below confidence threshold. Do not treat as a match.",
        )

    # OpenCLIP / DINOv2 cosine-style
    if score >= 0.30 and (gap is None or gap >= 0.02):
        return (
            "high",
            "Strong embedding similarity — still not a legal determination.",
        )
    if score >= 0.24:
        return (
            "medium",
            "Plausible visual similarity; expert review recommended.",
        )
    if score >= 0.18:
        return (
            "low",
            "Weak embedding signal; use as a research lead only.",
        )
    return (
        "uncertain",
        "Below confidence threshold. Do not treat as a match.",
    )
