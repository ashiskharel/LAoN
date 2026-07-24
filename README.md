# LAoN — Lost Ancient Arts of Nepal

**Photo a Nepali sculpture → find possible matches in open museum records and a curated catalog of documented objects.**

Mobile-first open-source web app for art aficionados, gallery visitors, students, and independent researchers. Nepal-first; designed so other regions can later add “country packs.”

> **Possible visual match — not a determination of legal ownership.**  
> LAoN does not file claims. See [docs/ethics.md](docs/ethics.md).

## Why this exists

Thousands of sacred sculptures left Nepal in the mid–late 20th century. Scholars documented many of them (notably Lain Singh Bangdel’s *Stolen Images of Nepal*, 1989). Museums publish open images. Activists and communities already match photos by hand.

LAoN is an **independent** tool that:

1. **Catalogs** a curated public set of objects (metadata + rights-cleared images)
2. **Matches** a phone photo against that index with visual similarity
3. **Exports** a shareable “possible match” evidence package for the user to send wherever they choose

It is **not** affiliated with NHRC, Lost Arts of Nepal, Himalayan Art Resources, Global Nepali Museum, or any museum. We credit public sources; we do not claim partnership.

## Dual corpus

| Layer | What | In git? |
|---|---|---|
| Public open subset | Metadata, CC0 museum images, licensed community photos | Yes |
| Private research corpus | Book plates / restricted research images you add locally | **No** (`data/private/`) |

Operators can set `PRIVATE_CORPUS_PATH` to improve match recall on a self-hosted instance. The default open demo uses public images only.

## Quick start

### Prerequisites

- Node 20+
- Python 3.11+

### API

```bash
cd services/api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Web

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000

### Optional: expand seed from open museum data

```bash
# From repo root, with services/api venv active
python scripts/ingest_cleveland.py --limit 30
python scripts/ingest_met.py --limit 40          # live Met API (sometimes blocked)
python scripts/ingest_met_csv.py --limit 40      # Met Open Access CSV fallback
python scripts/embed_corpus.py
# Then reload catalog if API is running:
# curl -X POST http://localhost:8000/api/admin/reload
```

## Repository layout

```
LAoN/
  apps/web/              Next.js PWA
  services/api/          FastAPI (catalog + visual search)
  packages/schema/       Shared JSON Schema for objects
  data/seed/             Public catalog JSON + geo
  data/private/          Local-only research images (gitignored)
  docs/                  Ethics, data sources, notes
  scripts/               Ingest + embed utilities
```

## MVP features

- Browse / filter catalog (status, place, iconography tags)
- Object detail with sources and museum links
- Simple map of original sites in the seed set
- Photo upload → ranked visual matches (embeddings when available; graceful fallback)
- Download “possible match” report JSON

## Stack

| Layer | Choice |
|---|---|
| Web | Next.js + TypeScript (PWA-ready) |
| API | FastAPI |
| Seed store (v1) | JSON files under `data/seed` |
| Vectors | NumPy cosine similarity; optional OpenCLIP embeddings |
| Museum data | Met Collection API (CC0), Cleveland Open Access (CC0) |

## Documentation

- [Ethics](docs/ethics.md)
- [Data sources](docs/data-sources.md)
- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## License

Code: [MIT](LICENSE).  
Catalog image licenses are **per image** (see each object’s `images[].license`). Prefer CC0 museum assets.

## Disclaimer

LAoN is a research and education project. Similarity results can be wrong. Always verify with specialists, primary sources, and proper legal channels before taking any public or legal action related to cultural property.
