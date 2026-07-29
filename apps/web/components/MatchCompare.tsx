"use client";

import Link from "next/link";
import {
  confidenceLabel,
  statusLabel,
  type MatchResponse,
} from "@/lib/api";

type Props = {
  queryPreviewUrl?: string | null;
  result: MatchResponse;
  /** When true, show report checkboxes / export is parent responsibility */
  selectable?: boolean;
  selected?: string[];
  onToggle?: (id: string) => void;
};

export default function MatchCompare({
  queryPreviewUrl,
  result,
  selectable,
  selected = [],
  onToggle,
}: Props) {
  const cropSrc = result.crop?.preview_jpeg_b64
    ? `data:image/jpeg;base64,${result.crop.preview_jpeg_b64}`
    : queryPreviewUrl || null;

  return (
    <div className="match-compare">
      <p className="meta">{result.disclaimer}</p>
      <p className="meta">{result.query_note}</p>

      {cropSrc && (
        <div className="panel">
          <div className="meta">
            Your photo (focused)
            {result.crop?.method ? ` · crop=${result.crop.method}` : ""}
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={cropSrc}
            alt="Query crop"
            className="compare-query-img"
          />
        </div>
      )}

      <h2>Possible matches</h2>
      {result.results.length === 0 ? (
        <p className="empty">
          No ranked image matches. Add public museum images or export research
          captures, then re-embed.
        </p>
      ) : (
        <div className="compare-list">
          {result.results.map((r) => {
            const thumb =
              r.matched_image_url || r.object.images?.[0]?.url || null;
            const tier = r.confidence || "uncertain";
            return (
              <article key={r.object.id} className={`compare-card tier-${tier}`}>
                <div className="compare-side-by-side">
                  <div className="compare-cell">
                    <div className="meta">Your photo</div>
                    {cropSrc ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={cropSrc} alt="" />
                    ) : (
                      <div className="compare-placeholder">—</div>
                    )}
                  </div>
                  <div className="compare-cell">
                    <div className="meta">Catalog</div>
                    {thumb ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={thumb} alt={r.object.titles[0]} />
                    ) : (
                      <div className="compare-placeholder">No image</div>
                    )}
                  </div>
                </div>
                <div className="compare-meta">
                  {selectable && (
                    <label className="compare-check">
                      <input
                        type="checkbox"
                        checked={selected.includes(r.object.id)}
                        onChange={() => onToggle?.(r.object.id)}
                      />
                      Include in report
                    </label>
                  )}
                  <span className={`badge confidence-${tier}`}>
                    {confidenceLabel(tier)}
                  </span>
                  <span className="score">
                    {(r.score * 100).toFixed(1)}%
                  </span>
                  <h3>
                    <Link href={`/objects/${r.object.id}`}>
                      {r.object.titles[0]}
                    </Link>
                  </h3>
                  <div className="meta">
                    {statusLabel(r.object.status)} · {r.method}
                  </div>
                  {r.confidence_note && (
                    <p className="meta confidence-note">{r.confidence_note}</p>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
