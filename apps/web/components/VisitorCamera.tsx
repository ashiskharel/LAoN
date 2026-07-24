"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  matchImage,
  statusLabel,
  type MatchResponse,
} from "@/lib/api";

type Mode = "camera" | "preview" | "results";

/**
 * Mobile-first visitor experience: live rear camera (when allowed) or
 * file/capture fallback, then match against LAoN catalog.
 */
export default function VisitorCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>("camera");
  const [liveReady, setLiveReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MatchResponse | null>(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setLiveReady(false);
  }, []);

  const startCamera = useCallback(async () => {
    setCameraError(null);
    stopCamera();
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setCameraError(
        "Live camera needs a secure context (HTTPS or localhost). Use “Choose photo” below."
      );
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setLiveReady(true);
      }
    } catch {
      setCameraError(
        "Could not open the rear camera. Allow camera permission, or pick a photo from your gallery."
      );
    }
  }, [stopCamera]);

  useEffect(() => {
    if (mode === "camera") {
      void startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [mode, startCamera, stopCamera]);

  function revokePreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }

  function setFromFile(f: File | null) {
    revokePreview();
    setFile(f);
    setResult(null);
    setError(null);
    if (f) {
      setPreviewUrl(URL.createObjectURL(f));
      setMode("preview");
    } else {
      setPreviewUrl(null);
      setMode("camera");
    }
  }

  async function captureFromLive() {
    const video = videoRef.current;
    if (!video || !liveReady) return;
    const w = video.videoWidth || 1280;
    const h = video.videoHeight || 720;
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.92)
    );
    if (!blob) return;
    const f = new File([blob], `laon-capture-${Date.now()}.jpg`, {
      type: "image/jpeg",
    });
    setFromFile(f);
  }

  async function runMatch() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await matchImage(file);
      setResult(res);
      setMode("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Match failed");
    } finally {
      setLoading(false);
    }
  }

  function resetAll() {
    setFromFile(null);
    setResult(null);
    setError(null);
    setMode("camera");
  }

  return (
    <div className="visitor-app">
      {mode === "camera" && (
        <>
          <div className="visitor-stage">
            {liveReady ? (
              <video
                ref={videoRef}
                className="visitor-video"
                playsInline
                muted
                autoPlay
              />
            ) : (
              <div className="visitor-placeholder">
                <p className="visitor-placeholder-title">Point at a sculpture</p>
                <p className="meta">
                  {cameraError ||
                    "Starting camera… On first use, allow camera access."}
                </p>
              </div>
            )}
            <div className="visitor-frame-guide" aria-hidden />
          </div>

          <div className="visitor-controls">
            <button
              type="button"
              className="visitor-secondary-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              Gallery
            </button>
            <button
              type="button"
              className="visitor-shutter"
              aria-label="Take photo"
              disabled={!liveReady}
              onClick={() => void captureFromLive()}
            />
            <button
              type="button"
              className="visitor-secondary-btn"
              onClick={() => void startCamera()}
            >
              Retry cam
            </button>
          </div>

          {!liveReady && (
            <div className="visitor-fallback">
              <button
                type="button"
                className="btn"
                onClick={() => fileInputRef.current?.click()}
              >
                Take or choose a photo
              </button>
              <p className="meta" style={{ textAlign: "center", marginTop: "0.75rem" }}>
                Works offline-prep on any phone browser. Add to Home Screen for
                an app-like icon.
              </p>
            </div>
          )}
        </>
      )}

      {mode === "preview" && previewUrl && (
        <>
          <div className="visitor-stage">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previewUrl} alt="Your capture" className="visitor-photo" />
          </div>
          <div className="visitor-actions">
            <button type="button" className="btn secondary" onClick={resetAll}>
              Retake
            </button>
            <button
              type="button"
              className="btn"
              disabled={loading}
              onClick={() => void runMatch()}
            >
              {loading ? "Finding matches…" : "Find possible matches"}
            </button>
          </div>
        </>
      )}

      {mode === "results" && result && (
        <div className="visitor-results">
          <div className="visitor-actions" style={{ marginBottom: "0.75rem" }}>
            <button type="button" className="btn" onClick={resetAll}>
              New photo
            </button>
          </div>

          <p className="meta">{result.disclaimer}</p>

          {result.crop?.preview_jpeg_b64 && (
            <div className="panel">
              <div className="meta">Focused region · {result.crop.method}</div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/jpeg;base64,${result.crop.preview_jpeg_b64}`}
                alt="Crop used for matching"
                className="visitor-crop-preview"
              />
            </div>
          )}

          <h2>Possible matches</h2>
          {result.results.length === 0 ? (
            <p className="empty">
              No strong image matches yet. Try a closer photo of the sculpture
              alone, or browse the{" "}
              <Link href="/catalog">catalog</Link>.
            </p>
          ) : (
            <ul className="visitor-match-list">
              {result.results.map((r) => {
                const thumb =
                  r.matched_image_url || r.object.images?.[0]?.url || null;
                return (
                  <li key={r.object.id}>
                    <Link href={`/objects/${r.object.id}`} className="visitor-match-card">
                      {thumb ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={thumb} alt="" />
                      ) : (
                        <div className="visitor-match-placeholder" />
                      )}
                      <div>
                        <strong>{r.object.titles[0]}</strong>
                        <div className="meta">
                          {statusLabel(r.object.status)} ·{" "}
                          {(r.score * 100).toFixed(0)}% similar
                        </div>
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {error && <div className="error visitor-error">{error}</div>}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="visually-hidden"
        onChange={(e) => setFromFile(e.target.files?.[0] || null)}
      />
    </div>
  );
}
