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
          {[obj.period, obj.original_site?.place, obj.current_location?.institution]
            .filter(Boolean)
            .join(" · ")}
        </div>
        {obj.iconography_tags?.length > 0 && (
          <div className="meta">{obj.iconography_tags.slice(0, 4).join(", ")}</div>
        )}
      </div>
    </article>
  );
}

type Props = {
  searchParams: Promise<{ q?: string; status?: string; place?: string }>;
};

export default async function CatalogPage({ searchParams }: Props) {
  const sp = await searchParams;
  let objects: CulturalObject[] = [];
  let total = 0;
  let error: string | null = null;

  try {
    const data = await fetchObjects({
      q: sp.q,
      status: sp.status,
      place: sp.place,
    });
    objects = data.objects;
    total = data.total;
  } catch {
    error = "API unavailable. Start the FastAPI server on port 8000.";
  }

  return (
    <>
      <h1>Catalog</h1>
      <p className="lead">
        Public subset of curated objects — metadata always public; images only when
        rights-cleared (CC0 museum, licensed community).
      </p>

      <form className="filters" method="get">
        <input
          type="search"
          name="q"
          placeholder="Search titles, tags, places…"
          defaultValue={sp.q || ""}
        />
        <select name="status" defaultValue={sp.status || ""}>
          <option value="">All statuses</option>
          <option value="stolen_documented">Documented stolen / missing</option>
          <option value="museum">In museum catalog</option>
          <option value="repatriated">Repatriated</option>
          <option value="in_situ">In situ</option>
          <option value="unknown">Unknown</option>
        </select>
        <input
          type="text"
          name="place"
          placeholder="Place (e.g. Patan)"
          defaultValue={sp.place || ""}
        />
        <button type="submit">Filter</button>
      </form>

      {error && <div className="error">{error}</div>}

      <p className="meta">{total} object{total === 1 ? "" : "s"}</p>

      {objects.length === 0 && !error ? (
        <p className="empty">No matches.</p>
      ) : (
        <div className="grid">
          {objects.map((o) => (
            <ObjectCard key={o.id} obj={o} />
          ))}
        </div>
      )}
    </>
  );
}
