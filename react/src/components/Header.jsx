import React from "react";
import "./Header.css";
import StatusChips from "./StatusChips";

export default function Header({
  docs,
  templateLabel,
  // criticalResolved,
  lowConf,
  missing,
}) {
  return (
    <div className="header card">
      <div className="headerRow">
        <div className="heading">
          <div className="title">
            Insurance Form Assistant — <span>Review &amp; Validate</span>
          </div>
          <div className="subtitle">
            Upload text-based PDFs → prefill → edit directly in the insurer PDF
            → save final PDF
          </div>
        </div>

        <div className="rightGroup">
          <span className="pill">{docs} docs</span>
          <span className="pill neutral">{templateLabel}</span>

          <StatusChips
            // criticalResolved={criticalResolved}
            lowConf={lowConf}
            missing={missing}
          />
        </div>
      </div>
    </div>
  );
}
