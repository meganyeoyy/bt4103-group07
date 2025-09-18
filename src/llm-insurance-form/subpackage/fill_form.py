import json
import os
import fitz
from typing import Dict, Tuple

def _as_on(value: str) -> bool:
    if value is None:
        return False
    s = str(value).strip().lower()
    if s == "":
        return False
    true_values = {"yes", "true", "on", "1", "checked", "x", "tick", "selected"}
    false_values  = {"no", "false", "off", "0", "unchecked"}
    if s in true_values:
        return True
    if s in false_values:
        return False
    return True

def _set_on_off(widget, on: bool) -> None:
    try:
        on_val  = widget.on_state()  if hasattr(widget, "on_state")  else "Yes"
        off_val = widget.off_state() if hasattr(widget, "off_state") else "Off"
        widget.field_value = on_val if on else off_val
        widget.update()
    except Exception as e:
        print(f"[warn] could not set widget '{widget.field_name}': {e}")

def _fit_text_to_width(widget: fitz.Widget, value: str, max_fs: float = 11.0,
                       min_fs: float = 6.0, pad: float = 2.0, fontname: str = "Helv") -> None:
    """
    Sets a font size that fits the longest line of 'value' within the widget's width.
    Uses Base-14 'Helv' to avoid font resource issues.
    """
    rect = fitz.Rect(widget.rect)
    avail = max(1.0, rect.width - 2 * pad)

    # Longest visual line
    lines = (value or "").splitlines() or [""]
    longest = max(lines, key=len)

    # Measure width at max_fs
    width_at_max = fitz.get_text_length(longest, fontname=fontname, fontsize=max_fs)
    if width_at_max <= avail:
        fs = max_fs
    else:
        fs = max(min_fs, (avail * max_fs) / max(1.0, width_at_max))

    widget.text_font = fontname
    widget.text_fontsize = fs
    widget.field_value = value
    widget.update()

def fill_from_json(input_pdf: str, json_path: str, output_pdf: str, flatten: bool = False) -> None:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    fields = data.get("fields", [])

    exact_map: Dict[Tuple[int, str], str] = {}
    name_map: Dict[str, list] = {}
    for it in fields:
        page = int(it.get("page", 0))
        name = (it.get("field_name") or "").strip()
        val  = it.get("field_value", "")
        if page and name:
            exact_map[(page, name)] = val
        if name:
            name_map.setdefault(name, []).append(val)

    doc = fitz.open(input_pdf)

    for page in doc:
        page_no = page.number + 1
        for w in (page.widgets() or []):
            fname = (w.field_name or "").strip()
            if not fname:
                continue

            value = None
            if (page_no, fname) in exact_map:
                value = exact_map[(page_no, fname)]
            else:
                vals = name_map.get(fname)
                if vals and len(vals) == 1:
                    value = vals[0]
            if value is None:
                continue

            t = w.field_type
            try:
                if t == fitz.PDF_WIDGET_TYPE_TEXT:
                    # Width-based auto fit to prevent cut-offs
                    _fit_text_to_width(w, "" if value is None else str(value), max_fs=11.0, min_fs=6.0)

                elif t == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    _set_on_off(w, on=_as_on(value))

                elif t == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                    _set_on_off(w, on=_as_on(value))

                elif t == fitz.PDF_WIDGET_TYPE_COMBOBOX:
                    choices = w.choice_values or []
                    is_editable_flag = getattr(fitz, "PDF_CH_FIELD_IS_EDIT", 1 << 18)
                    is_editable = bool((w.field_flags or 0) & is_editable_flag)
                    val_str = "" if value is None else str(value)
                    if is_editable or (choices and val_str in choices):
                        w.field_value = val_str
                        w.update()

                elif t == fitz.PDF_WIDGET_TYPE_LISTBOX:
                    choices = w.choice_values or []
                    val_str = "" if value is None else str(value)
                    if choices and val_str in choices:
                        w.field_value = val_str
                        w.update()

                elif t == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    pass

            except Exception as e:
                print(f"[warn] failed to set '{fname}' on page {page_no}: {e}")

    if flatten:
        if hasattr(doc, "bake"):
            doc.bake(widgets=True, annots=False)
        else:
            print("[info] Flatten skipped: your PyMuPDF version lacks Document.bake().")

    os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)
    doc.save(output_pdf, deflate=True)
    doc.close()
    print(f"Successfully wrote {output_pdf}")

if __name__ == "__main__":
    INPUT_PDF  = "data/pdf/ntuc_form.pdf"
    JSON_PATH  = "data/form_fields_filled.json"
    OUTPUT_PDF = "data/pdf/out/ntuc_form_filled.pdf"
    fill_from_json(INPUT_PDF, JSON_PATH, OUTPUT_PDF, flatten=False)
