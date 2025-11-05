import React from "react";
import "./FileList.css";

export default function FileList({ files, selected, onSelect, onRemove }) {
  return (
    <div className="fileList">
      {files.map((f) => (
        <button
          key={f.name}
          className={`fileRow ${selected === f.name ? "active" : ""}`}
          onClick={() => onSelect(f.name)}
          title={f.name}
        >
          <span className="dot" /> {f.name}
          <span className={`tag ${f.type}`}>{f.type}</span>
          <span
            className="x"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(f.name);
            }}
          >
            ×
          </span>
        </button>
      ))}
      {!files.length && <div className="empty small">No files yet.</div>}
    </div>
  );
}
