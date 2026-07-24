from pathlib import Path
import os

# Repo root: services/api/app/config.py -> parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("LAON_DATA_DIR", REPO_ROOT / "data"))
SEED_PATH = DATA_DIR / "seed" / "objects.json"
GEO_PATH = DATA_DIR / "geo" / "sites.geojson"
EMBEDDINGS_PATH = DATA_DIR / "embeddings" / "index.npz"
PRIVATE_CORPUS_PATH = Path(
    os.environ.get("PRIVATE_CORPUS_PATH", DATA_DIR / "private")
)
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_DIR = Path(os.environ.get("LAON_LOCAL_DIR", DATA_DIR / "local"))
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "LAON_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

DISCLAIMER = (
    "Possible visual match — not a determination of legal ownership. "
    "LAoN is an independent research tool and does not file claims."
)
