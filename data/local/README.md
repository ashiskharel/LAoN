# Local research database (gitignored)

This folder is created automatically when you use **Research capture** (`/research`).

| Path | Contents |
|---|---|
| `research.db` | SQLite database of Bangdel plate captures + labels |
| `images/bangdel/` | Your photos of book plates (private) |
| `captures_export.json` | Written by “Export for matching” |

## Workflow

1. Open http://localhost:3000/research  
2. Photograph a Bangdel plate; fill title, place/tole/temple, page, tags, notes  
3. **Save to local database**  
4. When ready: **Export for matching**  
   - copies images → `data/private/bangdel/`  
   - merges metadata → `data/seed/objects.json` (no public plate images)  
5. `python scripts/embed_corpus.py` then reload API catalog  

**Do not commit** `research.db` or plate images. Book plates are rights-restricted research material.
