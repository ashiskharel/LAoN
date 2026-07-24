import Link from "next/link";
import { fetchObjects, statusLabel } from "@/lib/api";
import type { CulturalObject } from "@/lib/api";

function ObjectCard({ obj }: { obj: CulturalObject }) {
  const img = obj.images?.[0];
  return (
    <article className="card">
      <div className="thumb">
        {img ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={img.url} alt={obj.titles[0]} />
        ) : (
          <span>No public image</span>
        )}
      </div>
      <div className="body">
        <span className={`badge ${obj.status}`}>{statusLabel(obj.status)}</span>
        <h3>
          <Link href={`/objects/${obj.id}`}>{obj.titles[0]}</Link>
        </h3>
        <div className="meta">
          {[obj.period, obj.material, obj.original_site?.place]
            .filter(Boolean)
            .join(" · ")}
        </div>
      </div>
    </article>
  );
}

export default async function HomePage() {
  let objects: CulturalObject[] = [];
  let error: string | null = null;
  try {
    const data = await fetchObjects();
    objects = data.objects.slice(0, 6);
  } catch {
    error =
      "Could not reach the API. Start it with: cd services/api && uvicorn app.main:app --reload --port 8000";
  }

  return (
    <>
      <h1>Find where Nepal&apos;s arts went</h1>
      <p className="lead">
        Browse a curated catalog of documented objects, explore original sites
        on a map, or photograph a sculpture to see possible visual matches in
        open museum data. Built for art aficionados of Nepal — open source,
        independent, research-first.
      </p>

      <div className="panel" style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
        <Link className="btn" href="/match">
          Match a photo
        </Link>
        <Link className="btn secondary" href="/catalog">
          Browse catalog
        </Link>
        <Link className="btn secondary" href="/map">
          Valley sites map
        </Link>
      </div>

      {error && <div className="error">{error}</div>}

      <h2>From the catalog</h2>
      {objects.length === 0 && !error ? (
        <p className="empty">No objects yet. Add seed data or run ingest scripts.</p>
      ) : (
        <div className="grid">
          {objects.map((o) => (
            <ObjectCard key={o.id} obj={o} />
          ))}
        </div>
      )}

      <p className="meta" style={{ marginTop: "1.5rem" }}>
        Expand the public seed with Met and Cleveland Open Access:{" "}
        <code>python scripts/ingest_met.py</code>
      </p>
    </>
  );
}
