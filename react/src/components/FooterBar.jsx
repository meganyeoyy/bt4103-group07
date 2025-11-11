import React from "react";
import "./FooterBar.css";

export default function FooterBar() {
  return (
    <div className="footer card section">
      <div className="left">
        Tip: you can edit values directly in the right PDF once generated.
      </div>
      <div className="right">
        <button className="primary" onClick={() => alert("Generate clicked")}>
          Generate
        </button>
      </div>
    </div>
  );
}
