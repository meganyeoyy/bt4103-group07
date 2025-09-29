import json
import re

# script transformed cleaned json into output for pdf population
# might need to change path structure depending on data filing

def split_date(date_str):
    """Split various date formats into (dd, mm, yyyy)."""
    if not date_str:
        return "", "", ""
    # dd/mm/yyyy
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", date_str)
    if m:
        return m.group(1), m.group(2), m.group(3)
    # yyyy-mm-dd
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        return m.group(3), m.group(2), m.group(1)
    # fallback
    return date_str, "", ""


def set_checkbox(field, value):
    """Set checkbox to Yes/No."""
    if "Yes" in field["field_name"] and value == "Yes":
        field["field_value"] = "Yes"
    elif "No" in field["field_name"] and value == "No":
        field["field_value"] = "Yes"
    else:
        field["field_value"] = ""


def map_combined_to_fields(combined, form_fields):
    for field in form_fields["fields"]:
        name = field["field_name"]

        # --- Period of records ---
        if "Over what period do your records extend? Start date" in name:
            dd, mm, yyyy = split_date(combined.get("Over what period do your records extend? Start date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        elif "Over what period do your records extend? End date" in name:
            dd, mm, yyyy = split_date(combined.get("Over what period do your records extend? End date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- First consultation ---
        elif "When did the Insured first consult you" in name:
            dd, mm, yyyy = split_date(combined.get("When did the Insured first consult you for this condition? (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        elif "symptoms presented" in name and "(1)" in name:
            field["field_value"] = combined.get("When you first saw the Insured, what were the symptoms presented and their duration? (1) Symptom presented", "")

        elif "duration of symptoms" in name and "(1)" in name:
            field["field_value"] = combined.get("When you first saw the Insured, what were the symptoms presented and their duration? (1) Duration of symptom", "")

        elif "date of onset" in name and "(1)" in name:
            field["field_value"] = combined.get("When you first saw the Insured, what were the symptoms presented and their duration? (1) Date of onset (dd/mm/yyyy)", "")

        # --- Other doctors consulted ---
        elif "Did the Insured consult any other doctors" in name:
            set_checkbox(field, combined.get("Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you?", ""))

        elif "Name of Doctor (1)" in name:
            field["field_value"] = combined.get("Details of other doctors consulted (rows) (1) Name of doctor", "")
        elif "clinic / hospital (1)" in name:
            field["field_value"] = combined.get("Details of other doctors consulted (rows) (1) Name and address of clinic / hospital", "")
        elif "Date(s) of consultation (dd/mm/yyyy) (1)" in name:
            field["field_value"] = combined.get("Details of other doctors consulted (rows) (1) Date(s) of consultation (dd/mm/yyyy)", "")
        elif "Diagnosis made (1)" in name:
            field["field_value"] = combined.get("Details of other doctors consulted (rows) (1) Diagnosis made", "")

        # --- Histological diagnosis ---
        elif "histological diagnosis" in name.lower():
            field["field_value"] = combined.get("Histological diagnosis", "")

        elif "Date of diagnosis" in name:
            dd, mm, yyyy = split_date(combined.get("Date of diagnosis (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        elif "where the diagnosis was first made" in name:
            field["field_value"] = combined.get("Doctor/clinic where diagnosis was first made", "")

        elif "when the Insured was first informed of the diagnosis" in name:
            dd, mm, yyyy = split_date(combined.get("Date Insured was first informed of diagnosis (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- Biopsy ---
        elif "Was a biopsy of the tumour performed" in name:
            set_checkbox(field, combined.get("Was a biopsy of the tumour performed?", ""))
        elif "date of biopsy" in name:
            dd, mm, yyyy = split_date(combined.get("Biopsy date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy
        elif "If “No”, please state why" in name:
            field["field_value"] = combined.get("If No, how was the diagnosis confirmed?", "")

        # --- Tumour details ---
        elif "site or organ involved" in name:
            field["field_value"] = combined.get("Site or organ involved", "")

        elif "staging" in name.lower():
            field["field_value"] = combined.get("Staging", "")

        elif "Has the cancer spread" in name:
            set_checkbox(field, combined.get("Has the cancer spread beyond the layer of cells?", ""))

        elif "Was the disease completely localised" in name:
            set_checkbox(field, combined.get("Was the disease completely localised?", ""))

        elif "Was there invasion of adjacent tissues" in name:
            set_checkbox(field, combined.get("Was there invasion of adjacent tissues?", ""))

        elif "Were regional lymph nodes involved" in name:
            set_checkbox(field, combined.get("Were regional lymph nodes involved?", ""))

        elif "Were there distant metastases" in name:
            set_checkbox(field, combined.get("Were there distant metastases?", ""))
        elif "metastases details" in name.lower():
            field["field_value"] = combined.get("Metastases details", "")

        # --- Special conditions (CIS, premalignant, etc.) ---
        elif "carcinoma-in-situ" in name.lower():
            set_checkbox(field, combined.get("Is the condition carcinoma-in-situ?", ""))
        elif "pre-malignant" in name.lower():
            set_checkbox(field, combined.get("Pre-malignant / non-invasive", ""))
        elif "borderline malignancy" in name.lower():
            set_checkbox(field, combined.get("Borderline / suspicious malignancy", ""))
        elif "Cervical Dysplasia" in name:
            set_checkbox(field, combined.get("Cervical dysplasia CIN1-3 (without CIS)", ""))

        elif "Carcinoma-in-situ of the Biliary" in name:
            set_checkbox(field, combined.get("Carcinoma-in-situ of biliary system", ""))

        elif "Hyperkeratoses" in name:
            set_checkbox(field, combined.get("Hyperkeratoses, basal/squamous skin cancers", ""))

        elif "Bladder Cancer" in name:
            set_checkbox(field, combined.get("Bladder cancer T1N0M0 or below", ""))
        elif "Papillary Micro-carcinoma of the Bladder" in name:
            set_checkbox(field, combined.get("Bladder papillary micro-carcinoma", ""))

        elif "Prostate cancer" in name:
            set_checkbox(field, combined.get("Is Prostate cancer T1N0M0, T1, or a equivalent or lesser classification?", ""))

        elif "Thyroid Cancer" in name:
            set_checkbox(field, combined.get("Is Thyriod cancer T1N0M0 or below?", ""))
        elif "size in diameter (cm)" in name and "Thyroid" in name:
            field["field_value"] = combined.get("Thyriod diameter", "")

        elif "Papillary Micro-carcinoma of the Thyroid" in name:
            set_checkbox(field, combined.get("Is Thyroid papillary micro-carcinoma?", ""))
        elif "size in diameter (cm)" in name and "Papillary Micro-carcinoma" in name:
            field["field_value"] = combined.get("Thyroid papillary micro-carcinoma size", "")

        # --- Leukaemia / Melanoma / GIST ---
        elif "leukaemia" in name.lower() and "type" in name.lower():
            field["field_value"] = combined.get("Leukaemia type", "")
        elif "RAI staging" in name:
            field["field_value"] = combined.get("Leukaemia RAI staging", "")
        elif "malignant melanoma" in name and "Breslow" in name:
            field["field_value"] = combined.get("Melanoma size/thickness (Breslow mm)", "")
        elif "malignant melanoma" in name and "Clark" in name:
            field["field_value"] = combined.get("Melanoma Clark level", "")
        elif "Has the condition caused invasion beyond the epidermis" in name:
            set_checkbox(field, combined.get("Has the condition caused invasion beyond the epidermis?", ""))
        elif "GIST" in name and "classification" in name:
            field["field_value"] = combined.get("GIST TNM classification", "")
        elif "GIST" in name and "Mitotic" in name:
            field["field_value"] = combined.get("GIST mitotic count (HPF)", "")

        # --- Treatments ---
        elif "treatment provided (1)" in name:
            if "type" in name.lower():
                field["field_value"] = combined.get("Has the patient received treatment for this illness? (1) Treatment details(rows) (1) Treatment type", "")
            elif "date" in name.lower():
                field["field_value"] = combined.get("Has the patient received treatment for this illness? (1) Treatment details(rows) (1) Date of treatment (dd/mm/yyyy)", "")
            elif "duration" in name.lower():
                field["field_value"] = combined.get("Has the patient received treatment for this illness? (1) Treatment details(rows) (1) Duration of treatment", "")

        elif "treatment provided (2)" in name:
            if "type" in name.lower():
                field["field_value"] = combined.get("Has the patient received treatment for this illness? (1) Treatment details(rows) (2) Treatment type", "")
            elif "date" in name.lower():
                field["field_value"] = combined.get("Has the patient received treatment for this illness? (1) Treatment details(rows) (2) Date of treatment (dd/mm/yyyy)", "")
            elif "duration" in name.lower():
                field["field_value"] = combined.get("Has the patient received treatment for this illness? (1) Treatment details(rows) (2) Duration of treatment", "")

        # --- Active treatment rejection ---
        elif "Has active treatment and therapy" in name:
            set_checkbox(field, combined.get("Has active treatment and therapy been rejected in favour of symptoms relief", ""))
        elif "Active treatment rejection reason" in name:
            field["field_value"] = combined.get("Active treatment rejection reason", "")

        # --- Surgeries ---
        elif "radical surgery" in name:
            set_checkbox(field, combined.get("Was radical surgery done?", ""))
        elif "surgical code" in name:
            field["field_value"] = combined.get("Radical surgery code/table", "")
        elif "date surgery" in name:
            dd, mm, yyyy = split_date(combined.get("Radical surgery date date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        elif "reconstructive surgery" in name:
            dd, mm, yyyy = split_date(combined.get("Reconstructive surgery date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- Follow-up / Discharge ---
        elif "Is the Insured still on follow-up" in name:
            set_checkbox(field, combined.get("Is the Insured still on follow-up at your clinic?", ""))
        elif "Next appointment" in name:
            dd, mm, yyyy = split_date(combined.get("Next appointment date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy
        elif "Discharge date" in name:
            dd, mm, yyyy = split_date(combined.get("Discharge date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- Terminal illness ---
        elif "terminally ill" in name:
            set_checkbox(field, combined.get("Is the Insured terminally ill (i.e. death expected within 12 months)?", ""))
        elif "Terminal illness evaluation" in name:
            field["field_value"] = combined.get("Terminal illness evaluation", "")
        elif "Terminal illness assessment date" in name:
            dd, mm, yyyy = split_date(combined.get("Terminal illness assessment date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- Hospice ---
        elif "hospice care" in name and ("Yes" in name or "No" in name):
            set_checkbox(field, combined.get("Is the Insured referred to hospice care?", ""))
        elif "Hospice name" in name:
            field["field_value"] = combined.get("Hospice name", "")
        elif "Hospice inpatient" in name:
            dd, mm, yyyy = split_date(combined.get("Hospice inpatient admission date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy
        elif "Hospice daycare" in name:
            dd, mm, yyyy = split_date(combined.get("Hospice daycare start date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- Consulted hospitals/doctors (multiple rows) ---
        elif "doctors/hospitals consulted" in name.lower():
            for i in range(1, 4):
                if f"(rows) ({i})" in name:
                    if "Name of doctor" in name:
                        field["field_value"] = combined.get(f"Doctors/hospitals consulted for this condition (rows) ({i}) Name of doctor", "")
                    elif "Clinic/Hospital" in name:
                        field["field_value"] = combined.get(f"Doctors/hospitals consulted for this condition (rows) ({i}) Name and Address of Clinic/Hospital", "")
                    elif "Date(s) of consultation" in name:
                        field["field_value"] = combined.get(f"Doctors/hospitals consulted for this condition (rows) ({i}) Date(s) of consultation (dd/mm/yyyy)", "")
                    elif "Diagnosis made" in name:
                        field["field_value"] = combined.get(f"Doctors/hospitals consulted for this condition (rows) ({i}) Diagnosis made", "")

        # --- Family / Medical / Lifestyle ---
        elif "malignant, pre-malignant or other related conditions" in name:
            set_checkbox(field, combined.get("Malignant, pre-malignant or other related conditions or risk factors?", ""))
        elif "risk factors details" in name.lower():
            field["field_value"] = combined.get("Malignant, pre-malignant or other related conditions or risk factors details", "")
        elif "Medical history" in name:
            field["field_value"] = combined.get("Medical history that would have increased the risk of cancer", "")
        elif "Family history" in name:
            field["field_value"] = combined.get("Family history that would have increased the risk of Cancer", "")
        elif "smoking" in name.lower():
            field["field_value"] = combined.get("Smoking habits", "")
        elif "alcohol" in name.lower():
            field["field_value"] = combined.get("Alcohol consumption habits", "")

        # --- HIV / AIDS ---
        elif "HIV" in name:
            field["field_value"] = combined.get("HIV antibody status", "")
        elif "HIV/AIDS diagnosis date" in name:
            dd, mm, yyyy = split_date(combined.get("HIV/AIDS diagnosis date (dd/mm/yyyy)", ""))
            if "(dd)" in name: field["field_value"] = dd
            elif "(mm)" in name: field["field_value"] = mm
            elif "(yyyy)" in name: field["field_value"] = yyyy

        # --- Other health conditions ---
        elif "other significant health condition" in name.lower():
            field["field_value"] = combined.get("Any other significant health conditions", "")

    return form_fields


with open("combined.json") as f:
    combined = json.load(f)
with open("form_fields.json") as f:
    form_fields = json.load(f)

updated = map_combined_to_fields(combined, form_fields)

with open("form_fields_filled.json", "w") as f:
    json.dump(updated, f, indent=4)

print("All form fields have been updated into form_fields_filled.json")
