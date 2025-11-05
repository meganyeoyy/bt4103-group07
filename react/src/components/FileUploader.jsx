import React, { useRef, useState } from "react";
import "./FileUploader.css";

export default function FileUploader({ onFiles }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);

  const accept = "application/pdf,.pdf";

  const handleFiles = (fileList) => {
    if (!fileList || !fileList.length) return;

    const all = [...fileList];
    const valid = [];
    const invalid = [];

    all.forEach((f) => {
      if (
        f.type === "application/pdf" ||
        f.name.toLowerCase().endsWith(".pdf")
      ) {
        valid.push(f);
      } else {
        invalid.push(f.name);
      }
    });

    if (invalid.length) {
      alert(
        `Only PDF files are accepted.\nIgnored:\n- ${invalid.join("\n- ")}`
      );
    }

    if (valid.length) onFiles(valid);
  };

  return (
    <div
      className={`uploader ${drag ? "drag" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        accept={accept}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="dash">Drag &amp; drop files or click to select</div>
      <div className="hint small">
        Upload <b>PDF</b> only (multiple) — single patient
      </div>
    </div>
  );
}
