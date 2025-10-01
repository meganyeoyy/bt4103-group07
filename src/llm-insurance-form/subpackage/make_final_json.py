import json
import re

# --- Utilities ---

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


def set_field_with_confidence(field, combined, key_base):
    """Set value + confidence for text fields."""
    value = combined.get(f"{key_base} value", "")
    confidence = combined.get(f"{key_base} confidence", "")
    field["field_value"] = value
    field["confidence"] = str(confidence) if confidence != "" else ""


def set_date_with_confidence(field, combined, key_base, name):
    """Set dd/mm/yyyy split fields with confidence."""
    date_str = combined.get(f"{key_base} value", "")
    confidence = combined.get(f"{key_base} confidence", "")
    dd, mm, yyyy = split_date(date_str)

    if "(dd)" in name:
        field["field_value"] = dd
    elif "(mm)" in name:
        field["field_value"] = mm
    elif "(yyyy)" in name:
        field["field_value"] = yyyy

    field["confidence"] = str(confidence) if confidence != "" else ""


def set_checkbox_with_confidence(field, combined, key_base):
    """Set Yes/No checkboxes with confidence."""
    value = combined.get(f"{key_base} value", "")
    confidence = combined.get(f"{key_base} confidence", "")

    if "Yes" in field["field_name"] and value == "Yes":
        field["field_value"] = "Yes"
    elif "No" in field["field_name"] and value == "No":
        field["field_value"] = "Yes"
    else:
        field["field_value"] = ""

    field["confidence"] = str(confidence) if confidence != "" else ""


# --- Mapper ---

def map_combined_to_fields(combined, form_fields):
    for field in form_fields["fields"]:
        name = field["field_name"]

        # --- Period of records ---
        if "Over what period do your records extend? Start date" in name:
            set_date_with_confidence(field, combined, "Over what period do your records extend? Start date (dd/mm/yyyy)", name)

        elif "Over what period do your records extend? End date" in name:
            set_date_with_confidence(field, combined, "Over what period do your records extend? End date (dd/mm/yyyy)", name)

        # --- First consultation ---
        elif "When did the Insured first consult you" in name:
            set_date_with_confidence(field, combined, "When did the Insured first consult you for this condition? (dd/mm/yyyy)", name)

        elif "duration of symptoms" in name and "(1)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (1) Duration of symptom")

        elif "date of onset" in name and "(1)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (1) Date of onset (dd/mm/yyyy)")

        elif "symptoms presented" in name and "(1)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (1) Symptom presented")
        
        elif "duration of symptoms" in name and "(2)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (2) Duration of symptom")

        elif "date of onset" in name and "(2)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (2) Date of onset (dd/mm/yyyy)")
        
        elif "symptoms presented" in name and "(2)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (2) Symptom presented")


        # --- Other doctors consulted ---
        elif "Details of other doctors consulted" and "Name of Doctor (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (1) Name of doctor")
        elif "Details of other doctors consulted" and  "clinic / hospital (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (1) Name and address of clinic / hospital")
        elif "Details of other doctors consulted" and "Date(s) of consultation (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (1) Date(s) of consultation (dd/mm/yyyy)")
        elif "Details of other doctors consulted" and "Diagnosis made (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (1) Diagnosis made")

        elif "Details of other doctors consulted" and "Name of Doctor (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (2) Name of doctor")
        elif "Details of other doctors consulted" and "clinic / hospital (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (2) Name and address of clinic / hospital")
        elif "Details of other doctors consulted" and "Date(s) of consultation (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (2) Date(s) of consultation (dd/mm/yyyy)")
        elif "Details of other doctors consulted" and "Diagnosis made (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (2) Diagnosis made")

        elif "Details of other doctors consulted" and "Name of Doctor (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (3) Name of doctor")
        elif "Details of other doctors consulted" and "clinic / hospital (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (3) Name and address of clinic / hospital")
        elif "Details of other doctors consulted" and "Date(s) of consultation (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (3) Date(s) of consultation (dd/mm/yyyy)")
        elif "Details of other doctors consulted" and "Diagnosis made (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows) (3) Diagnosis made")

        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you?" in name:
            set_checkbox_with_confidence(field, combined, "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you?")

        # --- Histological diagnosis ---
        elif "histological diagnosis" in name.lower():
            set_field_with_confidence(field, combined, "Histological diagnosis")

        elif "Date of diagnosis" in name:
            set_date_with_confidence(field, combined, "Date of diagnosis (dd/mm/yyyy)", name)

        elif "where the diagnosis was first made" in name:
            set_field_with_confidence(field, combined, "Doctor/clinic where diagnosis was first made")

        elif "when the Insured was first informed of the diagnosis" in name:
            set_date_with_confidence(field, combined, "Date Insured was first informed of diagnosis (dd/mm/yyyy)", name)

        # --- Biopsy ---
        elif "date of biopsy" in name:
            set_date_with_confidence(field, combined, "Biopsy date (dd/mm/yyyy)", name)
        elif "Was a biopsy of the tumour performed? If “No”, please state why and how the diagnosis was confirmed" in name:
            set_field_with_confidence(field, combined, "If No, how was the diagnosis confirmed?")
        elif "Was a biopsy of the tumour performed?" in name:
            set_checkbox_with_confidence(field, combined, "Was a biopsy of the tumour performed?")

        # --- Tumour details ---
        elif "site or organ involved" in name:
            set_field_with_confidence(field, combined, "Site or organ involved")

        elif "is the staging of the tumour?" in name:
            set_field_with_confidence(field, combined, "Staging")

        elif "Has the cancer spread" in name:
            set_checkbox_with_confidence(field, combined, "Has the cancer spread beyond the layer of cells?")
        elif "Was the disease completely localised" in name:
            set_checkbox_with_confidence(field, combined, "Was the disease completely localised?")
        elif "Was there invasion of adjacent tissues" in name:
            set_checkbox_with_confidence(field, combined, "Was there invasion of adjacent tissues?")
        elif "Were regional lymph nodes involved" in name:
            set_checkbox_with_confidence(field, combined, "Were regional lymph nodes involved?")
        elif "Were there distant metastases" in name:
            set_checkbox_with_confidence(field, combined, "Were there distant metastases?")
        elif "metastases details" in name.lower():
            set_field_with_confidence(field, combined, "Metastases details")

        # --- Special conditions (CIS, premalignant, etc.) ---
        elif "carcinoma-in-situ" in name.lower():
            set_checkbox_with_confidence(field, combined, "Is the condition carcinoma-in-situ?")
        elif "Is the condition pre-malignant or non-invasive?" in name:
            set_checkbox_with_confidence(field, combined, "Pre-malignant / non-invasive")
        elif "borderline malignancy" in name.lower():
            set_checkbox_with_confidence(field, combined, "Borderline / suspicious malignancy")
        elif "Cervical Dysplasia" in name:
            set_checkbox_with_confidence(field, combined, "Cervical dysplasia CIN1-3 (without CIS)")

        elif "Carcinoma-in-situ of the Biliary" in name:
            set_checkbox_with_confidence(field, combined, "Carcinoma-in-situ of biliary system")
        elif "Hyperkeratoses" in name:
            set_checkbox_with_confidence(field, combined, "Hyperkeratoses, basal/squamous skin cancers")
        elif "Bladder Cancer" in name:
            set_checkbox_with_confidence(field, combined, "Bladder cancer T1N0M0 or below")
        elif "Papillary Micro-carcinoma of the Bladder" in name:
            set_checkbox_with_confidence(field, combined, "Bladder papillary micro-carcinoma")

        elif "Prostate cancer" in name:
            set_checkbox_with_confidence(field, combined, "Is Prostate cancer T1N0M0, T1, or a equivalent or lesser classification?")
        elif "Thyroid Cancer" in name:
            set_checkbox_with_confidence(field, combined, "Is Thyriod cancer T1N0M0 or below?")
        elif "size in diameter (cm)" in name and "Thyroid" in name:
            set_field_with_confidence(field, combined, "Thyriod diameter")

        elif "Papillary Micro-carcinoma of the Thyroid" in name:
            set_checkbox_with_confidence(field, combined, "Is Thyroid papillary micro-carcinoma?")
        elif "size in diameter (cm)" in name and "Papillary Micro-carcinoma" in name:
            set_field_with_confidence(field, combined, "Thyroid papillary micro-carcinoma size")

        # --- Leukaemia / Melanoma / GIST ---
        elif "If the diagnosis is leukaemia, please state type of leukaemia" in name:
            set_field_with_confidence(field, combined, "Leukaemia type")
        elif "If the diagnosis is leukaemia, please state type of RAI staging" in name:
            set_field_with_confidence(field, combined, "Leukaemia RAI staging")
        elif "malignant melanoma" in name and "Breslow" in name:
            set_field_with_confidence(field, combined, "Melanoma size/thickness (Breslow mm)")
        elif "malignant melanoma" in name and "Clark" in name:
            set_field_with_confidence(field, combined, "Melanoma Clark level")
        elif "Has the condition caused invasion beyond the epidermis" in name:
            set_checkbox_with_confidence(field, combined, "Has the condition caused invasion beyond the epidermis?")
        elif "GIST" in name and "classification" in name:
            set_field_with_confidence(field, combined, "GIST TNM classification")
        elif "GIST" in name and "Mitotic" in name:
            set_field_with_confidence(field, combined, "GIST mitotic count (HPF)")

        # --- Treatments ---
            
        elif "Please provide full details of all type of treatment provided (1)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (1) Treatment type")
        elif "Please provide full details of date of treatment provided (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (1) Date of treatment (dd/mm/yyyy)")
        elif "Please provide full details of duration of treatment provided (1)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (1) Duration of treatment")

        elif "Please provide full details of all type of treatment provided (2)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (2) Treatment type")
        elif "Please provide full details of date of treatment provided (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (2) Date of treatment (dd/mm/yyyy)")
        elif "Please provide full details of duration of treatment provided (2)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (2) Duration of treatment")

        elif "Please provide full details of all type of treatment provided (3)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (3) Treatment type")
        elif "Please provide full details of date of treatment provided (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (3) Date of treatment (dd/mm/yyyy)")
        elif "Please provide full details of duration of treatment provided (3)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (3) Duration of treatment")

        # --- Active treatment rejection ---
        elif "Has active treatment and therapy" in name:
            set_checkbox_with_confidence(field, combined, "Has active treatment and therapy been rejected in favour of symptoms relief")
        elif "Active treatment rejection reason" in name:
            set_field_with_confidence(field, combined, "Active treatment rejection reason")

        # --- Surgeries ---
        elif "radical surgery" in name:
            set_checkbox_with_confidence(field, combined, "Was radical surgery done?")
        elif "surgical code" in name:
            set_field_with_confidence(field, combined, "Radical surgery code/table")
        elif "date surgery" in name:
            set_date_with_confidence(field, combined, "Radical surgery date date (dd/mm/yyyy)", name)

        elif "reconstructive surgery" in name:
            set_date_with_confidence(field, combined, "Reconstructive surgery date (dd/mm/yyyy)", name)

        # --- Follow-up / Discharge ---
        elif "Is the Insured still on follow-up at your clinic? If “Yes”, please provide state date of next appointment (dd/mm/yyyy)" in name:
            set_date_with_confidence(field, combined, "Next appointment date (dd/mm/yyyy)", name)
        elif "Is the Insured still on follow-up at your clinic? If \"No”, please provide date of discharge (dd/mm/yyyy)" in name:
            set_date_with_confidence(field, combined, "Discharge date (dd/mm/yyyy)", name)
        elif "Is the Insured still on follow-up" in name:
            set_checkbox_with_confidence(field, combined, "Is the Insured still on follow-up at your clinic?")
        
        # --- Terminal illness ---
        elif "terminally ill" in name:
            set_checkbox_with_confidence(field, combined, "Is the Insured terminally ill (i.e. death expected within 12 months)?")
        elif "Terminal illness evaluation" in name:
            set_field_with_confidence(field, combined, "Terminal illness evaluation")
        elif "Terminal illness assessment date" in name:
            set_date_with_confidence(field, combined, "Terminal illness assessment date (dd/mm/yyyy)", name)

        # --- Hospice ---
        elif "hospice care" in name and ("Yes" in name or "No" in name):
            set_checkbox_with_confidence(field, combined, "Is the Insured referred to hospice care?")
        elif "Hospice name" in name:
            set_field_with_confidence(field, combined, "Hospice name")
        elif "Hospice inpatient" in name:
            set_date_with_confidence(field, combined, "Hospice inpatient admission date (dd/mm/yyyy)", name)
        elif "Hospice daycare" in name:
            set_date_with_confidence(field, combined, "Hospice daycare start date (dd/mm/yyyy)", name)

        # --- Doctors/hospitals consulted (explicit mappings) ---

        elif "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (1) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (1) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (1) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (1) Diagnosis made")

        elif "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (2) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (2) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (2) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (2) Diagnosis made")

        elif "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (3) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (3) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (3) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (3) Diagnosis made")

        elif "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (4)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (4) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (4)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (4) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (4)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (4) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (4)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows) (4) Diagnosis made")

        # --- Family / Medical / Lifestyle ---
        elif "Has the Insured ever had any malignant, pre-malignant or other related conditions or risk factors? If “Yes”, please provide details, including diagnosis, date of diagnosis, dates of consultation, name and address of doctor/ clinic and source of information" in name:
            set_field_with_confidence(field, combined, "Malignant, pre-malignant or other related conditions or risk factors details")
        elif "Has the Insured ever had any malignant, pre-malignant or other related conditions or risk factors?" in name:
            set_checkbox_with_confidence(field, combined, "Malignant, pre-malignant or other related conditions or risk factors?")
        elif "medical history" in name:
            set_field_with_confidence(field, combined, "Medical history that would have increased the risk of cancer")
        elif "family history" in name:
            set_field_with_confidence(field, combined, "Family history that would have increased the risk of Cancer")
        elif "smoking" in name:
            set_field_with_confidence(field, combined, "Smoking habits")
        elif "alcohol" in name:
            set_field_with_confidence(field, combined, "Alcohol consumption habits")

        # --- HIV / AIDS ---
        elif "HIV antibody status" in name:
            set_field_with_confidence(field, combined, "HIV antibody status")
        elif "HIV/AIDS diagnosis date" in name:
            set_date_with_confidence(field, combined, "HIV/AIDS diagnosis date (dd/mm/yyyy)", name)

        # --- Other significant health conditions ---

        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of diagnosis (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (1) Diagnosis")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide name of doctor that diagnosed (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (1) Name of doctor")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Name and address of clinic/ hospital (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (1) Name/address of clinic/hospital")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of date of diagnosis (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (1) Date of diagnosis (dd/mm/yyyy)")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Duration of condition (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (1) Duration of condition")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of treatment received (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (1) Treatment received")
        
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of diagnosis (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (2) Diagnosis")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide name of doctor that diagnosed (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (2) Name of doctor")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Name and address of clinic/ hospital (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (2) Name/address of clinic/hospital")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of date of diagnosis (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (2) Date of diagnosis (dd/mm/yyyy)")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Duration of condition (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (2) Duration of condition")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of treatment received (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (2) Treatment received")

        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of diagnosis (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (3) Diagnosis")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide name of doctor that diagnosed (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (3) Name of doctor")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Name and address of clinic/ hospital (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (3) Name/address of clinic/hospital")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of date of diagnosis (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (3) Date of diagnosis (dd/mm/yyyy)")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Duration of condition (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (3) Duration of condition")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of treatment received (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows) (3) Treatment received")
        
        elif "Does Insured have or ever had any other significant health condition(s)?" in name:
            set_checkbox_with_confidence(field, combined, "Any other significant health conditions")

        

    return form_fields


# --- Run ---

with open("dummy_data.json") as f:
    combined = json.load(f)
with open("form_fields_empty.json") as f:
    form_fields = json.load(f)

updated = map_combined_to_fields(combined, form_fields)

with open("form_fields_filled.json", "w") as f:
    json.dump(updated, f, indent=4, ensure_ascii=False)

print("All form fields (with confidence) have been updated into form_fields_filled.json")
