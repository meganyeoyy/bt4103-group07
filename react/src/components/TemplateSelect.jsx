import React from "react";
import "./TemplateSelect.css";

const options = ["NTUC Income", "Great Eastern"];

export default function TemplateSelect({ value, onChange }) {
  return (
    <div className="templ">
      <label>Template</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">-- Select a template --</option>

        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>

      <div className="selected">
        Selected: <b>{value || "None"}</b>
      </div>
    </div>
  );
}
