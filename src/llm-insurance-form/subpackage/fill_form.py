import json
import os
import fitz  # PyMuPDF library for PDF manipulation
from typing import Dict, Tuple
import datetime

# ============================================================================
# HELPER FUNCTION: Set checkbox/radio button state
# ============================================================================
def _set_on_off(widget, should_check: bool) -> None:
    """
    Sets the state of a checkbox or radio button widget.
    
    Args:
        widget: PyMuPDF widget object (checkbox or radio button)
        should_check: Boolean indicating whether to check (True) or uncheck (False)
    """
    try:
        # Get the widget's "on" and "off" state values (usually "Yes"/"Off")
        on_val  = widget.on_state()  if hasattr(widget, "on_state")  else "Yes"
        off_val = widget.off_state() if hasattr(widget, "off_state") else "Off"
        
        # Set the appropriate value
        widget.field_value = on_val if should_check else off_val
        widget.update()  # Apply the change to the PDF
    except Exception as e:
        print(f"[warn] could not set widget '{widget.field_name}': {e}")

# ============================================================================
# HELPER FUNCTION: Auto-fit text to widget width
# ============================================================================
def _fit_text_to_width(widget: fitz.Widget, value: str, max_fs: float = 11.0,
                       min_fs: float = 6.0, pad: float = 2.0, fontname: str = "Helv") -> None:
    """
    Dynamically adjusts font size to fit text within the widget's width.
    Prevents text from being cut off in narrow fields.
    
    Args:
        widget: PyMuPDF text widget object
        value: Text string to be inserted
        max_fs: Maximum font size (default 11pt)
        min_fs: Minimum font size (default 6pt)
        pad: Padding on each side in points (default 2pt)
        fontname: Font name - using "Helv" (Helvetica) to avoid font resource issues
    """
    rect = fitz.Rect(widget.rect)
    # Calculate available width (widget width minus padding on both sides)
    avail = max(1.0, rect.width - 2 * pad)

    # Find the longest line in the text (handles multi-line values)
    lines = (value or "").splitlines() or [""]
    longest = max(lines, key=len)

    # Measure how wide the text would be at max font size
    width_at_max = fitz.get_text_length(longest, fontname=fontname, fontsize=max_fs)
    
    # If text fits at max size, use max size; otherwise scale down proportionally
    if width_at_max <= avail:
        fs = max_fs
    else:
        fs = max(min_fs, (avail * max_fs) / max(1.0, width_at_max))

    # Apply the calculated font size and value
    widget.text_font = fontname
    widget.text_fontsize = fs
    widget.field_value = value
    widget.update()  # Apply changes to the PDF

# ============================================================================
# MAIN FUNCTION: Fill PDF form from JSON data
# ============================================================================
def fill_from_json(input_pdf: str, json_path: str, output_pdf: str, flatten: bool = False) -> None:
    """
    Fills a PDF form with data from a JSON file.
    
    Args:
        input_pdf: Path to the source PDF with form fields
        json_path: Path to JSON file containing field data
        output_pdf: Path where filled PDF will be saved
        flatten: If True, converts form fields to static content (non-editable)
    """
    
    # ------------------------------------------------------------------------
    # STEP 1: Load and parse JSON data
    # ------------------------------------------------------------------------
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    fields = data.get("fields", [])

    # ------------------------------------------------------------------------
    # STEP 2: Build lookup maps for efficient field matching
    # ------------------------------------------------------------------------
    # Map (page_number, field_name) -> field_value for exact page+name matches
    exact_map: Dict[Tuple[int, str], str] = {}
    # Map field_name -> list of values (for fields appearing on multiple pages)
    name_map: Dict[str, list] = {}
    
    for it in fields:
        page = int(it.get("page", 0))
        name = (it.get("field_name") or "").strip()
        val  = it.get("field_value", "")
        
        # Store in exact map if both page and name are available
        if page and name:
            exact_map[(page, name)] = val
        # Store in name map for all fields with names
        if name:
            name_map.setdefault(name, []).append(val)

    # ------------------------------------------------------------------------
    # STEP 3: Open the PDF document
    # ------------------------------------------------------------------------
    doc = fitz.open(input_pdf)

    # ------------------------------------------------------------------------
    # STEP 4: Iterate through all pages and widgets (form fields)
    # ------------------------------------------------------------------------
    for page in doc:
        page_no = page.number + 1  # PyMuPDF uses 0-based indexing, convert to 1-based
        
        # Get all form field widgets on this page
        for w in (page.widgets() or []):
            fname = (w.field_name or "").strip()
            if not fname:
                continue  # Skip widgets without names

            # ----------------------------------------------------------------
            # STEP 4a: Find the value for this field
            # ----------------------------------------------------------------
            value = None
            
            # First, try exact match (page + field name)
            if (page_no, fname) in exact_map:
                value = exact_map[(page_no, fname)]
            else:
                # If no exact match, try matching by name alone
                # Only use this if the field name appears exactly once in the JSON
                vals = name_map.get(fname)
                if vals and len(vals) == 1:
                    value = vals[0]
            
            if value is None:
                continue  # No value found for this field, skip it

            # ----------------------------------------------------------------
            # STEP 4b: Fill the field based on its type
            # ----------------------------------------------------------------
            t = w.field_type
            try:
                # TEXT FIELD: Regular text input
                if t == fitz.PDF_WIDGET_TYPE_TEXT:
                    # Use auto-fit function to prevent text cutoff
                    _fit_text_to_width(w, "" if value is None else str(value), max_fs=11.0, min_fs=6.0)

                # CHECKBOX: On/off toggle
                # LLM outputs "Yes" in field_value when the checkbox should be ticked
                # Empty string or other values mean unchecked
                elif t == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    should_check = (str(value).strip().lower() == "yes")
                    _set_on_off(w, should_check)

                # RADIO BUTTON: Mutually exclusive options
                # LLM outputs "Yes" in field_value when the radio button should be selected
                elif t == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                    should_check = (str(value).strip().lower() == "yes")
                    _set_on_off(w, should_check)

                # COMBOBOX: Dropdown with optional text input
                elif t == fitz.PDF_WIDGET_TYPE_COMBOBOX:
                    choices = w.choice_values or []
                    # Check if the combobox allows custom text entry
                    is_editable_flag = getattr(fitz, "PDF_CH_FIELD_IS_EDIT", 1 << 18)
                    is_editable = bool((w.field_flags or 0) & is_editable_flag)
                    val_str = "" if value is None else str(value)
                    
                    # Only set value if it's in the choices OR the field is editable
                    if is_editable or (choices and val_str in choices):
                        w.field_value = val_str
                        w.update()

                # LISTBOX: Selection from a list
                elif t == fitz.PDF_WIDGET_TYPE_LISTBOX:
                    choices = w.choice_values or []
                    val_str = "" if value is None else str(value)
                    # Only set value if it exists in the available choices
                    if choices and val_str in choices:
                        w.field_value = val_str
                        w.update()

                # SIGNATURE: Digital signature field (skip filling)
                elif t == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    pass  # Signature fields require special handling

            except Exception as e:
                print(f"[warn] failed to set '{fname}' on page {page_no}: {e}")

    # ------------------------------------------------------------------------
    # STEP 5: Optionally flatten the PDF (make fields non-editable)
    # ------------------------------------------------------------------------
    if flatten:
        if hasattr(doc, "bake"):
            # "Bake" converts interactive fields to static content
            doc.bake(widgets=True, annots=False)
        else:
            print("[info] Flatten skipped: your PyMuPDF version lacks Document.bake().")

    # ------------------------------------------------------------------------
    # STEP 6: Save the filled PDF
    # ------------------------------------------------------------------------
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)
    # Save with deflate compression to reduce file size
    doc.save(output_pdf, deflate=True)
    doc.close()
    print(f"Successfully wrote {output_pdf}")

# ============================================================================
# SCRIPT EXECUTION: Run when file is executed directly
# ============================================================================
if __name__ == "__main__":
    # Define file paths
    INPUT_PDF  = "data/pdf/ntuc_form.pdf"
    JSON_PATH  = "data/raw-txt/form_fields_filled.json"
    OUTPUT_PDF = f"data/pdf/out/ntuc_form_filled_{datetime.datetime.now().strftime('%d-%m-%Y %H%M')}.pdf"
    
    # Execute the form filling process
    # Set flatten=False to keep fields editable, flatten=True to lock them
    fill_from_json(INPUT_PDF, JSON_PATH, OUTPUT_PDF, flatten=False)