import json
import fitz  # PyMuPDF library for PDF manipulation
from typing import Dict, Tuple, Union, List
import io

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
# MAIN FUNCTION: Fill PDF form and return as bytes (Flask-ready)
# ============================================================================
def fill_pdf_form(
    pdf_source: Union[str, bytes],
    form_data: Union[dict, str, List[dict]],
    flatten: bool = False
) -> bytes:
    """
    Fills a PDF form with data and returns the filled PDF as bytes.
    Perfect for Flask routes that serve PDFs directly.
    
    Args:
        pdf_source: Either a file path (str) or PDF bytes
        form_data: Either:
                   - A dict with "fields" key containing list of field dicts
                   - A JSON string representing the same structure
                   - A list of field dicts directly
        flatten: If True, converts form fields to static content (non-editable)
    
    Returns:
        bytes: The filled PDF as bytes, ready to be sent via Flask
        
    Example usage in Flask:
        @app.route('/fill-form', methods=['POST'])
        def fill_form():
            pdf_bytes = fill_pdf_form(
                pdf_source='template.pdf',
                form_data=request.json,
                flatten=False
            )
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name='filled_form.pdf'
            )
    """
    
    # ------------------------------------------------------------------------
    # STEP 1: Parse form data from various input formats
    # ------------------------------------------------------------------------
    if isinstance(form_data, str):
        # Parse JSON string
        data = json.loads(form_data)
        fields = data.get("fields", [])
    elif isinstance(form_data, list):
        # Direct list of fields
        fields = form_data
    elif isinstance(form_data, dict):
        # Dict with "fields" key or direct field mapping
        fields = form_data.get("fields", form_data if "field_name" in str(form_data) else [])
    else:
        raise ValueError("form_data must be dict, list, or JSON string")

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
    # STEP 3: Open the PDF document from file path or bytes
    # ------------------------------------------------------------------------
    if isinstance(pdf_source, bytes):
        doc = fitz.open(stream=pdf_source, filetype="pdf")
    else:
        doc = fitz.open(pdf_source)

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
    # STEP 6: Return the filled PDF as bytes
    # ------------------------------------------------------------------------
    # Write PDF to a bytes buffer instead of file
    pdf_bytes = doc.tobytes(deflate=True)
    doc.close()
    
    return pdf_bytes