"use client";

import { useState } from "react";
import Link from "next/link";
import {
  matchImage,
  buildReport,
  statusLabel,
  type MatchResponse,
} from "@/lib/api";

export default function MatchPage() {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [reportJson, setReportJson] = useState<string | null>(null);

  function onFile(f: File | null) {
    setFile(f);
    setResult(null);
    setReportJson(null);
    setSelected([]);
    setError(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  async function runMatch() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setReportJson(null);
    try {
      const res = await matchImage(file);
      setResult(res);
      setSelected(res.results.slice(0, 3).map((r) => r.object.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Match failed");
    } finally {
      setLoading(false);
    }
  }

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function exportReport() {
    if (!selected.length) return;
    try {
      const res = await buildReport({
        query_description: file?.name || "User photo",
        match_object_ids: selected,
        notes: "Generated from LAoN match UI",
      });
      const text = JSON.stringify(res, null, 2);
      setReportJson(text);
      const blob = new Blob([text], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `laon-possible-match-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Report failed");
    }
  }

  return (
    <>
      <h1>Match a photo</h1>
      <p className="lead">
        Upload a photo of a sculpture (museum gallery, phone snapshot, or scan).
        LAoN ranks possible visual matches from the public catalog. Scores are
        approximate — always verify with specialists.
      </p>

      <div className="panel">
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
              alt="Preview"
              style={{ maxHeight: 240, maxWidth: "100%", borderRadius: 8 }}
            />
          ) : (
            <div>
              <strong>Tap to take or choose a photo</strong>
              <p className="meta" style={{ margin: "0.5rem 0 0" }}>
                JPEG/PNG/WebP · max 12MB
              </p>
            </div>
          )}
        </label>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem" }}>
          <button type="button" disabled={!file || loading} onClick={runMatch}>
            {loading ? "Matching…" : "Find possible matches"}
          </button>
          {file && (
            <button
              type="button"
              className="secondary"
              onClick={() => onFile(null)}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <>
          <p className="meta">{result.disclaimer}</p>
          <p className="meta">{result.query_note}</p>

          <h2>Results</h2>
          {result.results.length === 0 ? (
            <p className="empty">
              No scored image matches yet. The seed catalog may need more public
              museum images — run ingest scripts, then{" "}
              <code>embed_corpus.py</code>.
            </p>
          ) : (
            <div className="panel" style={{ paddingTop: 0, paddingBottom: 0 }}>
              {result.results.map((r) => {
                const thumb =
                  r.matched_image_url || r.object.images?.[0]?.url || null;
                return (
                  <div className="match-row" key={r.object.id}>
                    {thumb ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={thumb} alt="" />
                    ) : (
                      <div
                        style={{
                          width: 88,
                          height: 88,
                          background: "#121814",
                          borderRadius: 8,
                        }}
                      />
                    )}
                    <div>
                      <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
                        <input
                          type="checkbox"
                          checked={selected.includes(r.object.id)}
                          onChange={() => toggle(r.object.id)}
                        />
                        <span>
                          <Link href={`/objects/${r.object.id}`}>
                            {r.object.titles[0]}
                          </Link>
                          <div className="meta">
                            {statusLabel(r.object.status)} · {r.method}
                          </div>
                        </span>
                      </label>
                    </div>
                    <div className="score">{(r.score * 100).toFixed(1)}%</div>
                  </div>
                );
              })}
            </div>
          )}

          <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            <button
              type="button"
              disabled={!selected.length}
              onClick={exportReport}
            >
              Download possible-match report (JSON)
            </button>
          </div>
          <p className="meta" style={{ marginTop: "0.75rem" }}>
            The report is for you to share with experts or authorities you trust.
            It is not a legal filing.
          </p>
          {reportJson && (
            <pre
              className="panel"
              style={{
                overflow: "auto",
                fontSize: "0.75rem",
                maxHeight: 240,
                marginTop: "1rem",
              }}
            >
              {reportJson}
            </pre>
          )}
        </>
      )}
    </>
  );
}
