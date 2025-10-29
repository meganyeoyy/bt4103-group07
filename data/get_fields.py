import fitz
from pathlib import Path
import json


FIELD_TYPE_MAP = {
    fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
    fitz.PDF_WIDGET_TYPE_TEXT: "text",
    fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "checkbox_delete",
}

def get_fields(file, out_json=f"data/raw-txt/GE_form_fields_empty.json"):    
    pdf = fitz.open(file)
    results = {"fields": []}

    page_no=1
    for page in pdf:
        widgets = page.widgets()
        for widget in widgets:
            field_type = FIELD_TYPE_MAP.get(widget.field_type, f"unknown ({widget.field_type})")
            print("Name:", widget.field_name, "Value:", widget.field_value, "Type:", field_type, "Page:", page_no)

            results["fields"].append(
                {
                    "field_name": widget.field_name,
                    "field_value": widget.field_value if widget.field_value else "",
                    "field_type": field_type,
                    "page": page_no,
                    "confidence": ""
                }
            )

        page_no+=1
    # Save to JSON file
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"Field metadata saved to {out_json}")
    return results


if __name__ == '__main__':
    # get_fields("data/pdf/ntuc_form.pdf")
    # get_fields("data/pdf/AIA Death.pdf")
    # get_fields("data/pdf/Great Eastern.pdf")
    get_fields("data/pdf/great_eastern_form.pdf")