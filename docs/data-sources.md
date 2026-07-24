# Data sources

## Public museum open access (ingest targets)

| Source | License / access | Notes |
|---|---|---|
| [Met Collection API](https://metmuseum.github.io/) | CC0 for open-access images | Primary seed: filter Nepal / Kathmandu Valley / Himalayan |
| [Met openaccess CSV](https://github.com/metmuseum/openaccess) | CC0 metadata | Bulk offline ingest |
| [Cleveland Museum of Art Open Access API](https://openaccess-api.clevelandart.org/) | CC0 | Secondary seed |
| [Smithsonian Open Access](https://www.si.edu/openaccess) | Open | Phase 2 |
| [Europeana APIs](https://api.europeana.eu/) | Varies; filter open reuse | Phase 2 |

## Documentary / scholarly (metadata + citations; images mixed)

| Source | Public subset | Private research corpus |
|---|---|---|
| Lain Singh Bangdel, *Stolen Images of Nepal* (1989) | Object metadata + bibliographic citation | Operator-scanned plates (not in git) |
| Jürgen Schick, *The Gods are Leaving the Country* | Same rule | Same rule |
| [Huntington Archive — Lost, Stolen, Damaged: Nepal](https://huntingtonarchive.org/resources/lostStolen/nepal.php) | Link-out; respect archive terms | Local research use only if terms allow |
| Published repatriation news (Met, Rubin, Dallas, etc.) | Case summaries + open images | — |

## Independent project — no formal affiliation

LAoN may **credit** and **link** to:

- Nepal Heritage Recovery Campaign (NHRC)
- Lost Arts of Nepal
- Himalayan Art Resources (HAR)
- Global Nepali Museum

It does **not** scrape private social feeds, claim partnership, or redistribute non-open datasets without permission.

## Dual-corpus layout

```
data/
  seed/                 # Public metadata + public image URLs (in git)
  geo/                  # Public GeoJSON for original sites
  private/              # LOCAL ONLY — book plates, restricted research images
  embeddings/           # Generated vectors (gitignored)
  cache/                # Downloaded museum images cache (gitignored)
```

Set `PRIVATE_CORPUS_PATH` (default `data/private`) when running the embedder/API so private images can improve match recall for self-hosted operators. The open demo runs on public images only.

## Per-image fields

Every image record should carry:

- `license` (e.g. `CC0`, `CC BY 4.0`, `restricted-research`)
- `attribution`
- `source_url`
- `visibility`: `public` | `private`
- `type`: `historical` | `museum` | `community` | `empty_niche`
