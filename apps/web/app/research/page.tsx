"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";

type Capture = {
  id: string;
  title: string;
  place?: string | null;
  tole?: string | null;
  temple?: string | null;
  bangdel_page?: string | null;
  bangdel_plate?: string | null;
  theft_date?: string | null;
  iconography_tags?: string[];
  notes?: string | null;
  image_relpath?: string | null;
  created_at?: string;
};

const emptyForm = {
  title: "",
  place: "",
  tole: "",
  temple: "",
  period: "",
  material: "",
  iconography_tags: "",
  theft_date: "",
  bangdel_page: "",
  bangdel_plate: "",
  provenance_notes: "",
  notes: "",
  linked_catalog_id: "",
  status: "stolen_documented",
};

export default function ResearchPage() {
  const [form, setForm] = useState(emptyForm);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  const load = useCallback(async () => {
    try {
      const sp = new URLSearchParams();
      if (q) sp.set("q", q);
      const res = await fetch(
        `${API_URL}/api/research/captures?${sp.toString()}`
      );
      if (!res.ok) throw new Error(`Load failed ${res.status}`);
      const data = await res.json();
      setCaptures(data.captures || []);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not load research DB. Is the API running?"
      );
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  function onFile(f: File | null) {
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  function setField(key: keyof typeof emptyForm, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) {
      setError("Title is required (e.g. deity name from Bangdel).");
      return;
    }
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const body = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (v) body.append(k, v);
      });
      if (file) body.append("file", file);
      const res = await fetch(`${API_URL}/api/research/captures`, {
        method: "POST",
        body,
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `Save failed ${res.status}`);
      }
      const data = await res.json();
      setMessage(`Saved capture ${data.capture?.id}`);
      setForm(emptyForm);
      onFile(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  async function onExport() {
    setExporting(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(
        `${API_URL}/api/research/export?sync_seed=true&copy_private=true`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error(`Export failed ${res.status}`);
      const data = await res.json();
      setMessage(
        `Exported: ${data.images_copied_to_private} images → private/, ` +
          `${data.metadata_synced_to_seed} metadata rows → seed. ` +
          `Next: run python scripts/embed_corpus.py`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm(`Delete capture ${id}?`)) return;
    await fetch(`${API_URL}/api/research/captures/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    await load();
  }

  return (
    <>
      <h1>Research capture</h1>
      <p className="lead">
        Local database for photographing Bangdel plates (and similar
        documentation). Stores labels, location, page numbers, and images on{" "}
        <strong>this machine only</strong> — not pushed to public git.
      </p>

      <div className="panel">
        <p className="meta" style={{ margin: 0 }}>
          SQLite: <code>data/local/research.db</code> · Images:{" "}
          <code>data/local/images/bangdel/</code>
        </p>
        <p className="meta">
          After a session, click <strong>Export for matching</strong> to copy
          plates into the private corpus and merge metadata into the catalog
          seed, then re-run embeddings.
        </p>
        <button
          type="button"
          className="secondary"
          disabled={exporting}
          onClick={() => void onExport()}
        >
          {exporting ? "Exporting…" : "Export for matching"}
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {message && (
        <div className="panel" style={{ borderColor: "rgba(111,191,138,0.4)" }}>
          {message}
        </div>
      )}

      <form className="panel research-form" onSubmit={onSubmit}>
        <h2 style={{ marginTop: 0 }}>New plate / object</h2>

        <label className="upload-zone">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => onFile(e.target.files?.[0] || null)}
          />
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={preview}
              alt="Plate preview"
              style={{ maxHeight: 220, maxWidth: "100%", borderRadius: 8 }}
            />
          ) : (
            <div>
              <strong>Photo of Bangdel plate (or empty niche)</strong>
              <p className="meta" style={{ margin: "0.4rem 0 0" }}>
                Tap to use camera or choose image
              </p>
            </div>
          )}
        </label>

        <div className="research-grid">
          <label>
            Title / deity *
            <input
              required
              value={form.title}
              onChange={(e) => setField("title", e.target.value)}
              placeholder="e.g. Uma-Mahesvara"
            />
          </label>
          <label>
            Iconography tags
            <input
              value={form.iconography_tags}
              onChange={(e) => setField("iconography_tags", e.target.value)}
              placeholder="uma-mahesvara, saiva, stone"
            />
          </label>
          <label>
            Place
            <input
              value={form.place}
              onChange={(e) => setField("place", e.target.value)}
              placeholder="Patan, Kathmandu, Changu Narayan…"
            />
          </label>
          <label>
            Tole / neighborhood
            <input
              value={form.tole}
              onChange={(e) => setField("tole", e.target.value)}
              placeholder="e.g. Saugal, Patko Tole"
            />
          </label>
          <label>
            Temple / site
            <input
              value={form.temple}
              onChange={(e) => setField("temple", e.target.value)}
            />
          </label>
          <label>
            Theft / loss date
            <input
              value={form.theft_date}
              onChange={(e) => setField("theft_date", e.target.value)}
              placeholder="e.g. 1985-05-16 or early 1980s"
            />
          </label>
          <label>
            Bangdel page
            <input
              value={form.bangdel_page}
              onChange={(e) => setField("bangdel_page", e.target.value)}
              placeholder="e.g. 246"
            />
          </label>
          <label>
            Plate / figure ref
            <input
              value={form.bangdel_plate}
              onChange={(e) => setField("bangdel_plate", e.target.value)}
              placeholder="e.g. plate 112"
            />
          </label>
          <label>
            Period
            <input
              value={form.period}
              onChange={(e) => setField("period", e.target.value)}
              placeholder="12th century"
            />
          </label>
          <label>
            Material
            <input
              value={form.material}
              onChange={(e) => setField("material", e.target.value)}
              placeholder="Grey limestone"
            />
          </label>
          <label>
            Status
            <select
              value={form.status}
              onChange={(e) => setField("status", e.target.value)}
            >
              <option value="stolen_documented">Documented stolen / missing</option>
              <option value="in_situ">In situ</option>
              <option value="repatriated">Repatriated</option>
              <option value="museum">In museum</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <label>
            Link catalog id (optional)
            <input
              value={form.linked_catalog_id}
              onChange={(e) => setField("linked_catalog_id", e.target.value)}
              placeholder="e.g. seed-surya-saugal-type"
            />
          </label>
        </div>

        <label className="full">
          Provenance / Bangdel caption notes
          <textarea
            rows={3}
            value={form.provenance_notes}
            onChange={(e) => setField("provenance_notes", e.target.value)}
            placeholder="Copy or paraphrase location description from the book…"
          />
        </label>
        <label className="full">
          Your notes
          <textarea
            rows={2}
            value={form.notes}
            onChange={(e) => setField("notes", e.target.value)}
          />
        </label>

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={loading}>
            {loading ? "Saving…" : "Save to local database"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setForm(emptyForm);
              onFile(null);
            }}
          >
            Clear form
          </button>
        </div>
      </form>

      <h2>Saved captures</h2>
      <div className="filters">
        <input
          type="search"
          placeholder="Search title, place, page…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button type="button" className="secondary" onClick={() => void load()}>
          Search
        </button>
      </div>

      {captures.length === 0 ? (
        <p className="empty">No local captures yet. Photograph a plate above.</p>
      ) : (
        <div className="research-list">
          {captures.map((c) => (
            <article key={c.id} className="panel research-item">
              <div className="research-item-row">
                {c.image_relpath ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`${API_URL}/api/research/captures/${encodeURIComponent(c.id)}/image`}
                    alt={c.title}
                    className="research-thumb"
                  />
                ) : (
                  <div className="research-thumb empty-thumb">No image</div>
                )}
                <div>
                  <strong>{c.title}</strong>
                  <div className="meta">
                    {[c.temple, c.tole, c.place].filter(Boolean).join(", ") ||
                      "No place set"}
                  </div>
                  <div className="meta">
                    {c.bangdel_page && <>p.{c.bangdel_page} · </>}
                    {c.bangdel_plate && <>{c.bangdel_plate} · </>}
                    {c.theft_date && <>lost {c.theft_date} · </>}
                    <code>{c.id}</code>
                  </div>
                  {c.iconography_tags && c.iconography_tags.length > 0 && (
                    <div className="meta">{c.iconography_tags.join(", ")}</div>
                  )}
                </div>
              </div>
              <div style={{ marginTop: "0.5rem" }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void onDelete(c.id)}
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <p className="meta" style={{ marginTop: "1.5rem" }}>
        <Link href="/visit">Visitor camera</Link> is for public matching. This
        page is for <strong>your research corpus</strong> (Bangdel rights stay
        private).
      </p>
    </>
  );
}
