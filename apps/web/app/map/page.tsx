import Link from "next/link";
import { fetchGeo, type GeoFeature } from "@/lib/api";

export default async function MapPage() {
  let features: GeoFeature[] = [];
  let error: string | null = null;

  try {
    const geo = await fetchGeo();
    features = geo.features || [];
  } catch {
    error = "Could not load geo data from API.";
  }

  // Simple list map for MVP — OSM link per pin (no heavy map lib yet)
  return (
    <>
      <h1>Original sites</h1>
      <p className="lead">
        Approximate locations for objects in the public seed set. Pins open
        OpenStreetMap. Coordinates are for awareness browsing — not cadastral
        precision.
      </p>

      {error && <div className="error">{error}</div>}

      <div className="map-list">
        {features.map((f, i) => {
          const props = f.properties || {};
          const coords =
            f.geometry && f.geometry.type === "Point"
              ? f.geometry.coordinates
              : null;
          const lng = coords?.[0] ?? null;
          const lat = coords?.[1] ?? null;
          const osm =
            lat != null && lng != null
              ? `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`
              : null;
          return (
            <div className="map-item" key={i}>
              <strong>{props.name || "Site"}</strong>
              {props.note && <p className="meta">{props.note}</p>}
              {props.object_ids && props.object_ids.length > 0 && (
                <p className="meta">
                  Objects:{" "}
                  {props.object_ids.map((id, j) => (
                    <span key={id}>
                      {j > 0 && ", "}
                      <Link href={`/objects/${id}`}>{id}</Link>
                    </span>
                  ))}
                </p>
              )}
              {osm && (
                <p style={{ margin: "0.35rem 0 0" }}>
                  <a href={osm} target="_blank" rel="noreferrer">
                    Open in OpenStreetMap
                  </a>
                  <span className="meta">
                    {" "}
                    · {lat?.toFixed(4)}, {lng?.toFixed(4)}
                  </span>
                </p>
              )}
            </div>
          );
        })}
      </div>

      {features.length === 0 && !error && (
        <p className="empty">No sites in data/geo/sites.geojson yet.</p>
      )}
    </>
  );
}
