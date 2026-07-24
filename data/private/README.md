# Private research corpus (local only)

Place rights-restricted research images here (e.g. personal photographs of Bangdel plates).  
**This directory is gitignored** (except this README and `.gitkeep`).

Suggested layout:

```
data/private/
  bangdel/
    plate-001.jpg
  schick/
  notes.md
```

Configure:

```bash
set PRIVATE_CORPUS_PATH=data/private   # Windows
export PRIVATE_CORPUS_PATH=data/private  # Unix
```

Then run `python scripts/embed_corpus.py` so private images can contribute embeddings on **your** machine only.

Do not upload these files to a public demo host unless you have redistributed rights.
