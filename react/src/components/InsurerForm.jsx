import React, { useEffect, useMemo, useRef } from "react";
import "./InsurerForm.css";
import { buildViewerSrc } from "../utils/url";

function decodeOverlaysB64(b64) {
  if (!b64) return [];
  try {
    return JSON.parse(atob(b64));
  } catch {
    return [];
  }
}

export default function InsurerForm({
  overlaysB64,
  generatedPdfUrl,
  isGenerating,
}) {
  const iframeRef = useRef(null);

  // Build viewer src only when there is a generated PDF
  const viewerSrc = useMemo(
    () => (generatedPdfUrl ? buildViewerSrc(generatedPdfUrl) : ""),
    [generatedPdfUrl]
  );

  // Apply overlays when PDF is ready
  useEffect(() => {
    if (!generatedPdfUrl) return;
    const iframe = iframeRef.current;
    if (!iframe || !viewerSrc) return;

    const overlays = decodeOverlaysB64(overlaysB64);

    const post = () => {
      const win = iframe.contentWindow;
      if (!win) return;
      win.postMessage(
        overlays.length
          ? { type: "apply-overlays", overlays }
          : { type: "clear-overlays" },
        "*"
      );
    };

    post();

    const onMsg = (e) => {
      if (
        e?.data?.type === "overlay-ready" &&
        e.source === iframe.contentWindow
      ) {
        post();
      }
    };

    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, [viewerSrc, overlaysB64, generatedPdfUrl]);

  // Show loading state when generating
  if (isGenerating) {
    return (
      <div className="card section insurer">
        <div className="panelHeader">
          <div className="panelTitle">Insurer Form — Review &amp; Edit</div>
        </div>
        <div className="pdfFrame">
          <div className="pdfViewport previewPlaceholder">
            <div className="spinner large" />
            <div className="placeholder big">Generating your filled PDF…</div>
          </div>
        </div>
      </div>
    );
  }

  // Show placeholder if no generated PDF
  if (!generatedPdfUrl) {
    return (
      <div className="card section insurer">
        <div className="panelHeader">
          <div className="panelTitle">Insurer Form — Review &amp; Edit</div>
        </div>
        <div className="pdfFrame">
          <div className="pdfViewport previewPlaceholder">
            <div className="fileName small">No generated form yet</div>
            <div className="placeholder small">
              Click <strong>Generate</strong> to produce the filled insurance
              form.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show generated PDF from backend
  return (
    <div className="card section insurer">
      <div className="panelHeader">
        <div className="panelTitle">Insurer Form — Review &amp; Edit</div>
      </div>
      <div className="pdfFrame">
        <div className="pdfViewport">
          <iframe
            key={viewerSrc}
            ref={iframeRef}
            className="pdfEmbed"
            title="Generated Filled PDF"
            src={viewerSrc}
            allow="clipboard-read; clipboard-write"
          />
        </div>
      </div>
    </div>
  );
}
