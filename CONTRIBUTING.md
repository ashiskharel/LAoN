# Contributing to LAoN

Thank you for helping document and surface Nepal’s cultural heritage with care.

## Before you start

1. Read [docs/ethics.md](docs/ethics.md) — especially soft language and “possible match ≠ claim.”
2. Read [docs/data-sources.md](docs/data-sources.md) — dual corpus and licensing rules.
3. Do **not** commit private research images, book scans, or API keys.

## Ways to contribute

- **Code** — web UI, API, ingest scripts, embedding pipeline
- **Seed data** — structured metadata for public objects (museum open access, published cases)
- **Geo** — original-site coordinates for empty niches / temples (with source notes)
- **Docs** — clarity for newcomers and operators
- **Evaluation pairs** — confirmed public match pairs for measuring visual search quality

## Development setup

### API (Python)

```bash
cd services/api
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Web (Node)

```bash
cd apps/web
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` if needed (default in `.env.example`).

### Seed & ingest

```bash
# From repo root, with API venv active:
python scripts/ingest_met.py --limit 30
python scripts/embed_corpus.py
```

## Pull request checklist

- [ ] No private/restricted images in the diff
- [ ] Each new public image has license + attribution + source URL
- [ ] UI copy avoids legal-claim language
- [ ] Seed JSON validates against the schema in `packages/schema`
- [ ] Docs updated if behavior or data rules change

## Code of conduct

Be respectful to communities whose deities and heritage are represented here. Disagreement about provenance is fine; hostility and harassment are not. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
