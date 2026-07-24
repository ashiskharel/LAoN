import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchObject, statusLabel } from "@/lib/api";

type Props = { params: Promise<{ id: string }> };

export default async function ObjectPage({ params }: Props) {
  const { id } = await params;
  let obj;
  try {
    obj = await fetchObject(id);
  } catch {
    notFound();
  }

  const img = obj.images?.[0];
  const site = obj.original_site;
  const loc = obj.current_location;

  return (
    <>
      <p className="meta">
        <Link href="/catalog">← Catalog</Link>
      </p>
      <span className={`badge ${obj.status}`}>{statusLabel(obj.status)}</span>
      <h1 style={{ marginTop: "0.5rem" }}>{obj.titles[0]}</h1>
      {obj.titles.length > 1 && (
        <p className="meta">Also known as: {obj.titles.slice(1).join("; ")}</p>
      )}

      <div className="detail-layout" style={{ marginTop: "1.25rem" }}>
        <div className="detail-image">
          {img ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={img.url} alt={obj.titles[0]} />
          ) : (
            <span className="meta" style={{ padding: "2rem" }}>
              No public image. Historical plates may exist only in a private
              research corpus.
            </span>
          )}
        </div>
        <div>
          <div className="panel">
            <div className="meta">Culture / period / material</div>
            <p style={{ margin: "0.25rem 0 0" }}>
              {[obj.culture, obj.period, obj.material].filter(Boolean).join(" · ") ||
                "—"}
            </p>
            {obj.dimensions && (
              <p className="meta" style={{ marginTop: "0.5rem" }}>
                {obj.dimensions}
              </p>
            )}
          </div>

          {site && (
            <div className="panel">
              <div className="meta">Original site (documented)</div>
              <p style={{ margin: "0.25rem 0 0" }}>
                {[site.temple, site.tole, site.place].filter(Boolean).join(", ") ||
                  "—"}
              </p>
              {site.geo && (
                <p className="meta">
                  Approx. {site.geo.lat.toFixed(3)}, {site.geo.lng.toFixed(3)}
                </p>
              )}
            </div>
          )}

          {loc && (
            <div className="panel">
              <div className="meta">Current location (as recorded)</div>
              <p style={{ margin: "0.25rem 0 0" }}>
                {loc.url ? (
                  <a href={loc.url} target="_blank" rel="noreferrer">
                    {loc.institution || loc.url}
                  </a>
                ) : (
                  loc.institution || "—"
                )}
              </p>
              {loc.accession && (
                <p className="meta">Accession: {loc.accession}</p>
              )}
              {loc.country && <p className="meta">{loc.country}</p>}
            </div>
          )}

          {obj.theft_date && (
            <div className="panel">
              <div className="meta">Documented theft / loss date</div>
              <p style={{ margin: "0.25rem 0 0" }}>{obj.theft_date}</p>
            </div>
          )}
        </div>
      </div>

      {obj.provenance_notes && (
        <>
          <h2>Notes</h2>
          <p className="lead" style={{ maxWidth: "none" }}>
            {obj.provenance_notes}
          </p>
        </>
      )}

      {obj.iconography_tags?.length > 0 && (
        <>
          <h2>Tags</h2>
          <p className="meta">{obj.iconography_tags.join(" · ")}</p>
        </>
      )}

      <h2>Sources</h2>
      <ul className="sources">
        {obj.sources.map((s, i) => (
          <li key={i}>
            {s.url ? (
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.label}
              </a>
            ) : (
              <strong style={{ color: "var(--text)" }}>{s.label}</strong>
            )}
            {s.citation && <> — {s.citation}</>}
          </li>
        ))}
      </ul>

      {img && (
        <p className="meta" style={{ marginTop: "1rem" }}>
          Image: {img.license}
          {img.attribution ? ` · ${img.attribution}` : ""}
        </p>
      )}
    </>
  );
}
