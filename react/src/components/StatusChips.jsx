import React from "react";
import "./StatusChips.css";

export default function StatusChips({ lowConf, missing }) {
  return (
    <div className="chips">
      {/* <span className="chip good">Critical resolved: {criticalResolved}</span> */}
      <span className="chip warn">Low conf: {lowConf}</span>
      <span className="chip bad">Missing: {missing}</span>
    </div>
  );
}
