/**
 * Transform extracted fields into overlay items for the viewer.
 * Input:  { fields: [{ field_name, field_value, field_type, page, confidence,
 *           top_left_pct:{x,y}, center_pct:{x,y}, size_pct:{w,h} }] }
 * Output: [{ page, xPct, yPct, label, class }]
 */

export function encodeFields(doc) {
  // single public API used by App.js
  const items = fieldsToOverlays(doc);
  return btoa(JSON.stringify(items));
}

/* ---------------- helpers ---------------- */

const toNumber = (x) => {
  const n = Number(x);
  return Number.isFinite(n) ? n : NaN;
};
const clampPct = (n) => Math.max(0, Math.min(100, n));
const normType = (t) =>
  String(t || "")
    .trim()
    .toLowerCase();
const CHECKBOX_DX_PCT = 10;
const DATE_DX_PCT = 4.5;
const CONF_THRESHOLD = 0.8;

function pickAnchorTopRightAbove(field) {
  // top right overlay
  const tl = field?.top_left_pct;
  const sz = field?.size_pct;
  const cp = field?.center_pct;
  if (
    tl &&
    sz &&
    typeof tl.x === "number" &&
    typeof tl.y === "number" &&
    typeof sz.w === "number" &&
    typeof sz.h === "number"
  ) {
    const name = String(field?.field_name || "").toLowerCase();

    // ✅ differentiate checkbox vs. date offset
    const isCheckbox = normType(field?.field_type).includes("checkbox");
    const isDateField = /\(dd\)|\(mm\)|\(yyyy\)/.test(name);

    let extraDx = 0;
    if (isCheckbox) extraDx = CHECKBOX_DX_PCT; // 8%
    else if (isDateField) extraDx = DATE_DX_PCT; // smaller 4%

    const xTR = tl.x + sz.w + extraDx;

    // slightly above center for better visibility
    return { xPct: clampPct(xTR), yPct: clampPct(cp.y - 1) };
  }
}

function isCheckboxField(f) {
  const ft = normType(f?.field_type);
  if (ft.includes("checkbox")) return true;
  const name = String(f?.field_name || "");
  return /\b(yes|no)\s*$/i.test(name.trim());
}

function baseCheckboxKey(f) {
  const name = String(f?.field_name || "").trim();
  const m = name.match(/^(.*?)(?:\s*[:\-–—]?\s*\(?\b(?:yes|no)\b\)?\s*)$/i);
  return m ? m[1].trim() || null : null;
}

/* ---------------- main transform ---------------- */

export function fieldsToOverlays(doc) {
  const fields = Array.isArray(doc?.fields) ? doc.fields : [];
  const out = [];

  /* ---------- group helpers ---------- */
  const groups = new Map(); // for yes/no checkboxes
  const dateGroups = new Map(); // for (dd/mm/yyyy)
  const singles = [];

  const isDatePartField = (f) => {
    const name = String(f?.field_name || "")
      .trim()
      .toLowerCase();
    // ✅ Match only fields ending with (dd), (mm), or (yyyy)
    return /\(\s*(dd|mm|yyyy)\s*\)$/.test(name);
  };

  const baseDateKey = (f) => {
    let name = String(f?.field_name || "")
      .trim()
      .toLowerCase();

    // ✅ Normalize smart quotes and apostrophes
    name = name
      .replace(/[“”«»„‟"]/g, '"') // replace any curly or angled quotes with straight quote
      .replace(/[‘’‚‛']/g, "'"); // normalize single quotes

    // ✅ Strip trailing (dd)/(mm)/(yyyy)
    name = name.replace(/\(\s*(dd|mm|yyyy)\s*\)\s*$/i, "");

    // ✅ Collapse multiple spaces/dashes
    name = name.replace(/[\s\-–—]+/g, " ").trim();

    return name;
  };

  /* ---------- partition fields ---------- */
  for (const f of fields) {
    if (isCheckboxField(f)) {
      const base = baseCheckboxKey(f);
      if (base) {
        if (!groups.has(base)) groups.set(base, []);
        groups.get(base).push(f);
        continue;
      }
    }

    if (isDatePartField(f)) {
      const base = baseDateKey(f);
      if (base) {
        if (!dateGroups.has(base)) dateGroups.set(base, []);
        dateGroups.get(base).push(f);
        continue;
      }
    }

    singles.push(f);
  }

  /* ---------- checkbox logic ---------- */
  for (const [, items] of groups) {
    const anchorField = items.length >= 2 ? items[1] : items[items.length - 1];

    const vals = items.map((f) => String(f?.field_value ?? "").trim());
    const confs = items.map((f) => toNumber(f?.confidence));
    const bothEmpty = vals.every((v) => v === "");

    let show = false;
    let label = "";
    let klass = "";

    if (bothEmpty) {
      show = true;
      label = "Missing";
      klass = "missing";
    } else {
      const lowExists = items.some((f, i) => {
        const answered = vals[i] !== "";
        const c = confs[i];
        return answered && Number.isFinite(c) && c < CONF_THRESHOLD;
      });
      if (lowExists) {
        show = true;
        label = "Low";
        klass = "low";
      }
    }

    if (show) {
      let page = Number(anchorField?.page);
      if (!Number.isFinite(page)) continue;
      if (page === 0) page = 1;

      const pos = pickAnchorTopRightAbove(anchorField);
      if (!pos) continue;
      out.push({ page, xPct: pos.xPct, yPct: pos.yPct, label, class: klass });
    }
  }

  /* ---------- date triplet logic ---------- */
  for (const [, items] of dateGroups) {
    if (items.length < 3) continue; // skip incomplete sets

    // pick last (yyyy) field as anchor for label placement
    const anchorField =
      items.find((f) => f.field_name.toLowerCase().includes("(yyyy)")) ||
      items[1] ||
      items[0];

    const vals = items.map((f) => String(f?.field_value ?? "").trim());
    const confs = items
      .map((f) => toNumber(f?.confidence))
      .filter((c) => Number.isFinite(c));

    const missingAny = vals.some((v) => v === "");
    const avgConf = confs.length
      ? confs.reduce((a, b) => a + b, 0) / confs.length
      : NaN;

    let show = false;
    let label = "";
    let klass = "";

    if (missingAny) {
      show = true;
      label = "Missing";
      klass = "missing";
    } else if (Number.isFinite(avgConf) && avgConf < CONF_THRESHOLD) {
      show = true;
      label = "Low";
      klass = "low";
    }

    if (show) {
      let page = Number(anchorField?.page);
      if (!Number.isFinite(page)) continue;
      if (page === 0) page = 1;

      const pos = pickAnchorTopRightAbove(anchorField);
      if (!pos) continue;
      out.push({ page, xPct: pos.xPct, yPct: pos.yPct, label, class: klass });
    }
  }

  /* ---------- single-field logic ---------- */
  for (const f of singles) {
    let page = Number(f?.page);
    if (!Number.isFinite(page)) continue;
    if (page === 0) page = 1;

    const isMissing = (f?.field_value ?? "") === "";
    const conf = toNumber(f?.confidence);
    const isLow = !isMissing && Number.isFinite(conf) && conf < CONF_THRESHOLD;
    if (!isMissing && !isLow) continue;

    const pos = pickAnchorTopRightAbove(f);
    if (!pos) continue;

    out.push({
      page,
      xPct: pos.xPct,
      yPct: pos.yPct,
      label: isMissing ? "Missing" : "Low",
      class: isMissing ? "missing" : "low",
    });
  }

  return out;
}
