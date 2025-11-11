import React, { useMemo } from "react";
import "./SourcePreview.css";
import { absoluteUrl } from "../utils/url";

export default function SourcePreview({ file }) {
  const viewerSrc = useMemo(() => {
    if (!file?.url) return null;
    const fileAbs = absoluteUrl(file.url);

    return `/pdfjs5/web/viewer.html?file=${encodeURIComponent(
      fileAbs
    )}&v=${Date.now().toString().slice(0, 7)}`;
  }, [file]);

  return (
    <div className="card section sourceBox">
      <div className="title">Source Document Preview</div>
      <div className="preview">
        {viewerSrc ? (
          <iframe
            key={viewerSrc} // ensures rerender when switching
            className="srcPdf"
            title={file.name}
            src={viewerSrc}
          />
        ) : (
          <>
            <div className="fileName small">No file selected</div>
            <div className="placeholder small">
              (Upload a PDF and select it from the list to preview here)
            </div>
          </>
        )}
      </div>
    </div>
  );
}
