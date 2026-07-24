const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Status =
  | "in_situ"
  | "stolen_documented"
  | "museum"
  | "private"
  | "repatriated"
  | "unknown";

export type CulturalObject = {
  id: string;
  titles: string[];
  culture?: string | null;
  period?: string | null;
  material?: string | null;
  dimensions?: string | null;
  iconography_tags: string[];
  status: Status;
  original_site?: {
    place?: string | null;
    tole?: string | null;
    temple?: string | null;
    geo?: { lat: number; lng: number } | null;
  } | null;
  current_location?: {
    institution?: string | null;
    accession?: string | null;
    url?: string | null;
    country?: string | null;
  } | null;
  provenance_notes?: string | null;
  theft_date?: string | null;
  sources: { label: string; url?: string | null; citation?: string | null }[];
  images: {
    url: string;
    type: string;
    license: string;
    attribution?: string | null;
    source_url?: string | null;
    visibility: string;
  }[];
};

export type MatchResult = {
  object: CulturalObject;
  score: number;
  method: string;
  matched_image_url?: string | null;
};

export type MatchResponse = {
  disclaimer: string;
  query_note: string;
  results: MatchResult[];
};

export async function fetchObjects(params?: {
  q?: string;
  status?: string;
  tag?: string;
  place?: string;
}): Promise<{ disclaimer: string; total: number; objects: CulturalObject[] }> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.status) sp.set("status", params.status);
  if (params?.tag) sp.set("tag", params.tag);
  if (params?.place) sp.set("place", params.place);
  const qs = sp.toString();
  const res = await fetch(`${API_URL}/api/objects${qs ? `?${qs}` : ""}`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchObject(id: string): Promise<CulturalObject> {
  const res = await fetch(`${API_URL}/api/objects/${encodeURIComponent(id)}`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) throw new Error(`Not found`);
  return res.json();
}

export type GeoFeature = {
  type: "Feature";
  properties?: {
    name?: string;
    object_ids?: string[];
    note?: string;
  } | null;
  geometry?: {
    type: string;
    coordinates: number[];
  } | null;
};

export type GeoCollection = {
  type: "FeatureCollection";
  features: GeoFeature[];
};

export async function fetchGeo(): Promise<GeoCollection> {
  const res = await fetch(`${API_URL}/api/geo`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`Geo error`);
  return res.json();
}

export async function matchImage(file: File, topK = 8): Promise<MatchResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/match?top_k=${topK}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Match failed ${res.status}`);
  }
  return res.json();
}

export async function buildReport(body: {
  query_description?: string;
  match_object_ids: string[];
  notes?: string;
}): Promise<{ disclaimer: string; generated_at: string; report: unknown }> {
  const res = await fetch(`${API_URL}/api/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Report failed`);
  return res.json();
}

export function statusLabel(s: Status): string {
  const map: Record<Status, string> = {
    in_situ: "In situ",
    stolen_documented: "Documented stolen / missing",
    museum: "In museum catalog",
    private: "Private collection",
    repatriated: "Repatriated / returned",
    unknown: "Unknown",
  };
  return map[s] || s;
}

export { API_URL };
