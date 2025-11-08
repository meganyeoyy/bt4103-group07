import json
import re
from pathlib import Path

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
    # dd-mmm-yyyy
    m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{4})", date_str)
    if m:
        cal = {
            "Jan": "01",
            "Feb": "02",
            "Mar": "03",
            "Apr": "04",
            "May": "05",
            "Jun": "06",
            "Jul": "07",
            "Aug": "08",
            "Sep": "09",
            "Oct": "10",
            "Nov": "11",
            "Dec": "12"
        }
        month = m.group(2)
        month_num = cal.get(month)
        return m.group(1), month_num, m.group(3)
    # ddmmyy
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})", date_str)
    if m:
        year = m.group(3)
        new_year = "20" + year
        return m.group(1), m.group(2), new_year
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

def set_delete_with_confidence(field, combined, key_base):
    """Set Yes/No delete fields with confidence."""
    value = combined.get(f"{key_base} value", "")
    confidence = combined.get(f"{key_base} confidence", "")

    if "Yes" in field["field_name"] and value == "No":
        field["field_value"] = "X"
    elif "No" in field["field_name"] and value == "Yes":
        field["field_value"] = "X"
    else:
        field["field_value"] = ""

    field["confidence"] = str(confidence) if confidence != "" else ""

# only for GE form, where unique field needs to be deleted
def set_source_with_confidence(field, combined, key_base):
    """Set Yes/No delete fields with confidence."""
    value = combined.get(f"{key_base} value", "")
    confidence = combined.get(f"{key_base} confidence", "")

    field_name = field["field_name"]

    # Case 1: If the selected value is "Patient"
    if value == "Patient":
        if "Referring Doctor" in field_name or "Others" in field_name:
            field["field_value"] = "X"
        elif "Patient" in field_name:
            field["field_value"] = ""
        else:
            field["field_value"] = ""

    # Case 2: If the selected value is "Referring Doctor"
    elif value == "Referring Doctor":
        if "Patient" in field_name or "Others" in field_name:
            field["field_value"] = "X"
        elif "Referring Doctor" in field_name:
            field["field_value"] = ""
        else:
            field["field_value"] = ""

    # Case 3: If the selected value is "Others"
    elif value == "Others":
        if "Patient" in field_name or "Referring Doctor" in field_name:
            field["field_value"] = "X"
        elif "Others" in field_name:
            field["field_value"] = ""
        else:
            field["field_value"] = ""

    # Default
    else:
        field["field_value"] = ""

    # Set confidence if present
    field["confidence"] = str(confidence) if confidence != "" else ""

# --- Mapper ---
def map_combined_to_fields_ntuc(combined, form_fields):
    for field in form_fields["fields"]:
        name = field["field_name"]

        # --- Page 1 ---
        # --- Doctors/hospitals consulted (explicit mappings) ---
        if "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (1) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (1) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (1) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (1)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (1) Diagnosis made")

        if "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (2) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (2) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (2) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (2)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (2) Diagnosis made")

        if "Please provide the date(s) of consultations at listed clinics/hospitals to which the Insured has attended for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (3) Date(s) of consultation (dd/mm/yyyy)")
        elif "Please provide the name of doctor(s) which the Insured has been referred to for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (3) Name of doctor")
        elif "Please provide the name and address of clinics/hospitals to which the Insured has attended for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (3) Name and Address of Clinic/Hospital")
        elif "Please provide details of diagnosis made during the consultation(s) at listed clinics/hospitals to which the Insured has attended for this condition (3)" in name:
            set_field_with_confidence(field, combined, "Doctors/hospitals consulted for this condition (rows 0..3) (3) Diagnosis made")

        elif "Has the Insured ever had any malignant, pre-malignant or other related conditions or risk factors? If “Yes”, please provide details, including diagnosis, date of diagnosis, dates of consultation, name and address of doctor/ clinic and source of information" in name:
            set_field_with_confidence(field, combined, "Malignant, pre-malignant or other related conditions or risk factors details")
        elif "Has the Insured ever had any malignant, pre-malignant or other related conditions or risk factors?" in name:
            set_checkbox_with_confidence(field, combined, "Malignant, pre-malignant or other related conditions or risk factors?")

        # --- Period of records ---
        elif "Over what period do your records extend? Start date" in name:
            set_date_with_confidence(field, combined, "Over what period do your records extend? Start date (dd/mm/yyyy)", name)

        elif "Over what period do your records extend? End date" in name:
            set_date_with_confidence(field, combined, "Over what period do your records extend? End date (dd/mm/yyyy)", name)

        # --- First consultation ---
        elif "When did the Insured first consult you" in name:
            set_date_with_confidence(field, combined, "When did the Insured first consult you for this condition? (dd/mm/yyyy)", name)

        elif "duration of symptoms" in name and "(1)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (rows 0..2) (1) Duration of symptom")

        elif "date of onset" in name and "(1)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (rows 0..2) (1) Date of onset (dd/mm/yyyy)")

        elif "symptoms presented" in name and "(1)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (rows 0..2) (1) Symptom presented")

        elif "duration of symptoms" in name and "(2)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (rows 0..2) (2) Duration of symptom")

        elif "date of onset" in name and "(2)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (rows 0..2) (2) Date of onset (dd/mm/yyyy)")

        elif "symptoms presented" in name and "(2)" in name:
            set_field_with_confidence(field, combined, "When you first saw the Insured, what were the symptoms presented and their duration? (rows 0..2) (2) Symptom presented")

        # --- Other doctors consulted ---
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Name of Doctor (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (1) Name of doctor")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and  "clinic / hospital (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (1) Name and address of clinic / hospital")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Date(s) of consultation (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (1) Date(s) of consultation (dd/mm/yyyy)")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Diagnosis made (1)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (1) Diagnosis made")

        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Name of Doctor (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (2) Name of doctor")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and  "clinic / hospital (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (2) Name and address of clinic / hospital")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Date(s) of consultation (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (2) Date(s) of consultation (dd/mm/yyyy)")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Diagnosis made (2)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (2) Diagnosis made")

        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Name of Doctor (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (3) Name of doctor")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and  "clinic / hospital (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (3) Name and address of clinic / hospital")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Date(s) of consultation (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (3) Date(s) of consultation (dd/mm/yyyy)")
        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you? If “Yes”," and "Diagnosis made (3)" in name:
            set_field_with_confidence(field, combined, "Details of other doctors consulted (rows 0..3) (3) Diagnosis made")

        elif "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you?" in name:
            set_checkbox_with_confidence(field, combined, "Did the Insured consult any other doctors for this illness or its symptoms before he/she consulted you?")

        # --- Histological diagnosis ---
        elif "histological diagnosis" in name.lower():
            set_field_with_confidence(field, combined, "Histological diagnosis")

        elif "Date of diagnosis (dd/mm/yyyy):" in name:
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
        elif "Were there distant metastases? If “Yes”, please provide full details, including site of any metastases, etc" in name:
            set_field_with_confidence(field, combined, "Metastases details")
        elif "Were there distant metastases" in name:
            set_checkbox_with_confidence(field, combined, "Were there distant metastases?")

        # --- Special conditions (CIS, premalignant, etc.) ---
        elif "Is the condition carcinoma-in-situ?" in name:
            set_checkbox_with_confidence(field, combined, "Is the condition carcinoma-in-situ?")
        elif "Is the condition pre-malignant or non-invasive?" in name:
            set_checkbox_with_confidence(field, combined, "Pre-malignant / non-invasive")
        elif "borderline malignancy" in name:
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
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (1) Treatment type")
        elif "Please provide full details of date of treatment provided (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (1) Date of treatment (dd/mm/yyyy)")
        elif "Please provide full details of duration of treatment provided (1)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (1) Duration of treatment")

        elif "Please provide full details of all type of treatment provided (2)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (2) Treatment type")
        elif "Please provide full details of date of treatment provided (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (2) Date of treatment (dd/mm/yyyy)")
        elif "Please provide full details of duration of treatment provided (2)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (2) Duration of treatment")

        elif "Please provide full details of all type of treatment provided (3)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (3) Treatment type")
        elif "Please provide full details of date of treatment provided (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (3) Date of treatment (dd/mm/yyyy)")
        elif "Please provide full details of duration of treatment provided (3)" in name:
            set_field_with_confidence(field, combined, "Has the patient received treatment for this illness? (rows 0..3) (3) Duration of treatment")

        # --- Active treatment rejection ---
        elif "Has active treatment and therapy" in name:
            set_checkbox_with_confidence(field, combined, "Has active treatment and therapy been rejected in favour of symptoms relief")
        elif "Active treatment rejection reason" in name:
            set_field_with_confidence(field, combined, "Active treatment rejection reason")

        # --- Surgeries ---
        elif "Was radical surgery (total and complete removal of the affected organ) done? If “Yes”, please state the name of the surgery, surgical code/table" in name:
            set_field_with_confidence(field, combined, "Radical surgery code/table")
        elif "Was radical surgery (total and complete removal of the affected organ) done? If “Yes”, please state the date surgery was performed" in name:
            set_date_with_confidence(field, combined, "Radical surgery date (dd/mm/yyyy)", name)
        elif "Was radical surgery (total and complete removal of the affected organ) done?" in name:
            set_checkbox_with_confidence(field, combined, "Was radical surgery done?")

        elif "For mastectomy cases, was reconstructive surgery done or recommended? If “Yes”, please state date surgery was performed" in name:
            set_date_with_confidence(field, combined, "Reconstructive surgery date (dd/mm/yyyy)", name)
        elif "For mastectomy cases, was reconstructive surgery done or recommended?" in name:
            set_checkbox_with_confidence(field, combined, "For mastectomy cases, was reconstructive surgery done or recommended?")

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
        elif "Is the Insured terminally ill, ie death is expected within 12 months? If “Yes”, please provide details on the basis of your evaluation" in name:
            set_field_with_confidence(field, combined, "Terminal illness evaluation")
        elif "the Insured terminally ill, ie death is expected within 12 months? If “Yes”, please indicate the date on which the Insured is assessed to be terminally ill" in name:
            set_date_with_confidence(field, combined, "Terminal illness assessment date (dd/mm/yyyy)", name)
        elif "Is the Insured terminally ill, ie death is expected within 12 months?" in name:
            set_checkbox_with_confidence(field, combined, "Is the Insured terminally ill (i.e. death expected within 12 months)?")

        # --- Hospice ---
        elif "name of hospice" in name:
            set_field_with_confidence(field, combined, "Hospice name")

        elif "Is the Insured referred to hospice care? If inpatient, please state date of admission" in name:
            set_date_with_confidence(field, combined, "Hospice inpatient admission date (dd/mm/yyyy)", name)
        elif "Is the Insured referred to hospice care? If yes, please state if it is inpatient" in name:
            set_field_with_confidence(field, combined, "Hospice care type - Inpatient")

        elif "Is the Insured referred to hospice care? If day care, please state start date (dd/mm/yyyy)" in name:
            set_date_with_confidence(field, combined, "Hospice daycare start date (dd/mm/yyyy)", name)
        elif "Is the Insured referred to hospice care? If yes, please state if it is day care" in name:
            set_field_with_confidence(field, combined, "Hospice care type - Day care")


        elif "hospice care" in name and ("Yes" in name or "No" in name):
            set_checkbox_with_confidence(field, combined, "Is the Insured referred to hospice care?")

        # --- Family / Medical / Lifestyle ---

        elif "Please give details of the Insured’s medical history which would have increased the risk of Cancer (including nature of illness, date of diagnosis and source of information)" in name:
            set_field_with_confidence(field, combined, "Medical history that would have increased the risk of cancer")
        elif "Please give details of the Insured’s family history which would have increased the risk of Cancer (including the relationship, nature of illness, date of  diagnosis and source of information)" in name:
            set_field_with_confidence(field, combined, "Family history that would have increased the risk of Cancer")
        elif "Please give details of the Insured’s habits in relation to past and present smoking, including the duration of smoking habits, number of cigarettes smoked  per day and source of this information" in name:
            set_field_with_confidence(field, combined, "Smoking habits")
        elif "Please give details of the Insured’s habits in relation to alcohol consumption, including the type of alcohol, amount of alcohol consumption per day,  duration of such consumption and source of this information" in name:
            set_field_with_confidence(field, combined, "Alcohol consumption habits")

        elif "Is the tumour or cancer in any way caused directly or indirectly by alcohol or drug abuse?" in name:
            set_checkbox_with_confidence(field, combined, "Is the tumour or cancer in any way caused directly or indirectly by alcohol or drug abuse?")


        # --- HIV / AIDS ---
        elif "Is the tumour in the presence of Human Immunodeficiency Virus (HIV) or Acquired Immune Deficiency Syndrome (AIDS)? If “Yes” please state HIV antibody status" in name:
            set_field_with_confidence(field, combined, "HIV antibody status")
        elif "Is the tumour in the presence of Human Immunodeficiency Virus (HIV) or Acquired Immune Deficiency Syndrome (AIDS)? If “Yes” please state date of diagnosis for HIV/AIDS (dd/mm/yyyy)" in name:
            set_date_with_confidence(field, combined, "HIV/AIDS diagnosis date (dd/mm/yyyy)", name)
        elif "Is the tumour in the presence of Human Immunodeficiency Virus (HIV) or Acquired Immune Deficiency Syndrome (AIDS)?" in name:
            set_checkbox_with_confidence(field, combined, "Tumour caused by HIV or AIDS?")


        # --- Other significant health conditions ---

        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of diagnosis (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (1) Diagnosis")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide name of doctor that diagnosed (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (1) Name of doctor")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Name and address of clinic/ hospital (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (1) Name/address of clinic/hospital")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of date of diagnosis (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (1) Date of diagnosis (dd/mm/yyyy)")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Duration of condition (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (1) Duration of condition")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of treatment received (1)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (1) Treatment received")

        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of diagnosis (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (2) Diagnosis")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide name of doctor that diagnosed (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (2) Name of doctor")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Name and address of clinic/ hospital (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (2) Name/address of clinic/hospital")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of date of diagnosis (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (2) Date of diagnosis (dd/mm/yyyy)")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Duration of condition (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (2) Duration of condition")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of treatment received (2)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (2) Treatment received")

        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of diagnosis (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (3) Diagnosis")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide name of doctor that diagnosed (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (3) Name of doctor")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Name and address of clinic/ hospital (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (3) Name/address of clinic/hospital")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of date of diagnosis (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (3) Date of diagnosis (dd/mm/yyyy)")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of Duration of condition (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (3) Duration of condition")
        elif "Does Insured have or ever had any other significant health condition(s)? If “Yes”, please provide details of treatment received (3)" in name:
            set_field_with_confidence(field, combined, "Details of other health conditions (rows 0..3) (3) Treatment received")

        elif "Does Insured have or ever had any other significant health condition(s)?" in name:
            set_checkbox_with_confidence(field, combined, "Any other significant health conditions")

    return form_fields

def map_combined_to_fields_ge(combined, form_fields):
    for field in form_fields["fields"]:
        name = field["field_name"]

        # --- Page 1 ---
        if "Date when insured first consulted you for cancer" in name:
            set_field_with_confidence(field, combined, "Date when insured first consulted you for cancer (ddmmyyyy)")

        elif "Please state symptoms presented (1)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (1) Symptom")
        elif "Please state duration of symptoms presented (1)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (1) Duration of symptom")
        elif "Please state the date that the symptoms first appeared (1)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (1) Date symptoms first started (dd/mm/yyyy)")

        elif "Please state symptoms presented (2)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (2) Symptom")
        elif "Please state duration of symptoms presented (2)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (2) Duration of symptom")
        elif "Please state the date that the symptoms first appeared (2)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (2) Date symptoms first started (dd/mm/yyyy)")

        elif "Please state symptoms presented (3)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (3) Symptom")
        elif "Please state duration of symptoms presented (3)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (3) Duration of symptom")
        elif "Please state the date that the symptoms first appeared (3)" in name:
            set_field_with_confidence(field, combined, "Please state symptoms presented and date symptoms first appeared (rows 0..3) (3) Date symptoms first started (dd/mm/yyyy)")

        elif "What is the source of the above information? If \"Referring Doctor / Others\", please specify name (1)" in name:
            set_field_with_confidence(field, combined, "What is the source of the above information? If Referring Doctor / Others, specify name & address (rows 0..2) (1) Name")
        elif "What is the source of the above information? If \"Referring Doctor / Others\", please specify address (1)" in name:
            set_field_with_confidence(field, combined, "What is the source of the above information? If Referring Doctor / Others, specify name & address (rows 0..2) (1) Address")

        elif "What is the source of the above information? If \"Referring Doctor / Others\", please specify name (2)" in name:
            set_field_with_confidence(field, combined, "What is the source of the above information? If Referring Doctor / Others, specify name & address (rows 0..2) (2) Name")
        elif "What is the source of the above information? If \"Referring Doctor / Others\", please specify address (2)" in name:
            set_field_with_confidence(field, combined, "What is the source of the above information? If Referring Doctor / Others, specify name & address (rows 0..2) (2) Address")

        elif "What is the source of the above information?" in name:
            set_source_with_confidence(field, combined, "Source of above information")

        elif "Diagnosis was first made by (name of Doctor)" in name:
            set_field_with_confidence(field, combined, "Diagnosis was first made by (name of Doctor)")
        elif "Date when Cancer was FIRST diagnosed" in name:
            set_field_with_confidence(field, combined, "Date when Cancer was FIRST diagnosed (ddmmyyyy)")

        # --- Page 2 ---
        elif "Actual diagnosis" in name:
            set_field_with_confidence(field, combined, "Actual diagnosis")
        elif "Date when insured first became aware of this illness (ddmmyyyy)" in name:
            set_field_with_confidence(field, combined, "Date when insured first became aware of this illness (ddmmyyyy)")

        elif "Was the illness suffered by Life Assured caused directly or indirectly by alcohol or drug abuse? If \"yes\", please give details" in name:
            set_field_with_confidence(field, combined, "If illness caused directly or indirectly by alcohol or drug abuse, please give details")
        elif "Was the illness suffered by Life Assured caused directly or indirectly by alcohol or drug abuse?" in name:
            set_delete_with_confidence(field, combined, "Was the illness suffered by Life Assured caused directly or indirectly by alcohol or drug abuse?")

        elif "staging of the tumour" in name:
            set_field_with_confidence(field, combined, "What is the staging of the tumour?")
        elif "tumour classification" in name:
            set_field_with_confidence(field, combined, "Please state the tumour classification (eg TMN classification etc)")

        elif "Was the cancer completely localised?" in name:
            set_delete_with_confidence(field, combined, "Was the cancer completely localised?")
        elif "Was there invasion of tissues?" in name:
            set_delete_with_confidence(field, combined, "Was there invasion of tissues?")
        elif "Were regional lymph nodes involved?" in name:
            set_delete_with_confidence(field, combined, "Were regional lymph nodes involved?")
        elif "Were there distant metastases?" in name:
            set_delete_with_confidence(field, combined, "Were there distant metastases?")

        elif "Did the Life Assured undergo any surgery? If \"Yes\", please indicate the surgical procedure performed" in name:
            set_field_with_confidence(field, combined, "Surgical procedure performed")
        elif "Did the Life Assured undergo any surgery? If \"Yes\", state the date of surgery (ddmmyyyy)" in name:
            set_field_with_confidence(field, combined, "Date of surgery (ddmmyyyy)")
        elif "Did the Life Assured undergo any surgery?" in name:
            set_delete_with_confidence(field, combined, "Did the Life Assured undergo any surgery?")

        elif "Was there any other mode of treatment, other than surgery, which could be undertaken to treat the Life Assured's condition? If \"YES\", please specify type of treatment" in name:
            set_field_with_confidence(field, combined, "Type of treatment other than surgery that could be undertaken to treat condition")
        elif "Was there any other mode of treatment, other than surgery, which could be undertaken to treat the Life Assured's condition?" in name:
            set_delete_with_confidence(field, combined, "Was there any other mode of treatment, other than surgery, which could be undertaken to treat the Life Assured’s condition?")

        # --- Page 3 ---
        elif "Has the Life Assured underwent other mode of treatment? If \"Yes\", please state date of treatment (ddmmyyyy)" in name:
            set_field_with_confidence(field, combined, "Date of other treatment (ddmmyyyy)")
        elif "Has the Life Assured underwent other mode of treatment? If \"No\", please state why not" in name:
            set_field_with_confidence(field, combined, "Reason for no other mode of treatment")
        elif "Has the Life Assured underwent other mode of treatment?" in name:
            set_delete_with_confidence(field, combined, "Has the Life Assured undergone other mode of treatment?")


        elif "What other forms of treatment did the Life Assured undergo" in name:
            set_field_with_confidence(field, combined, "What other forms of treatment did the Life Assured undergo (eg chemotherapy, radiotherapy etc)?")
        elif "If diagnosis is leukaemia" in name:
            set_field_with_confidence(field, combined, "If diagnosis is leukaemia, please provide the type of leukaemia")
        elif "malignant melanoma" in name:
            set_field_with_confidence(field, combined, "If the diagnosis is malignant melanoma, please give full details of size, thickness (Breslow classification) and/or depth of invasion (Clark level)")

        elif "Is the diagnosis related to Human Immunodeficiency Virus (HIV) or Acquired Immune Deficiency Syndrome (AIDS)? If \"Yes\", please provide the date of diagnosis for HIV / AIDS (ddmmyyyy)" in name:
            set_field_with_confidence(field, combined, "Date of diagnosis for HIV/AIDS (ddmmyyyy)")
        elif "Is the diagnosis related to Human Immunodeficiency Virus (HIV) or Acquired Immune Deficiency Syndrome (AIDS)?" in name:
            set_delete_with_confidence(field, combined, "Is the diagnosis related to Human Immunodeficiency Virus (HIV) or Acquired Immune Deficiency Syndrome (AIDS)?")

        elif "Please describe the Life Assured's mental and cognitive abilities" in name:
            set_field_with_confidence(field, combined, "Life Assured’s mental and cognitive abilities")
        elif "Is the Life Assured mentally capable in accordance to the Mental Capacity Act (Chapter 177A of Singapore)? " in name:
            set_delete_with_confidence(field, combined, "Is Life Assured mentally capable?")

        # --- Page 4 ---
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state medical condition (1)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (1) Medical condition")
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state date of diagnosis (dd/mm/yyyy) (1)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (1) Diagnosis date (dd/mm/yyyy)")
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state name & address of treating doctor (1)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (1) Name & address of treating doctor")

        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state medical condition (2)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (2) Medical condition")
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state date of diagnosis (dd/mm/yyyy) (2)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (2) Diagnosis date (dd/mm/yyyy)")
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state name & address of treating doctor (2)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (2) Name & address of treating doctor")

        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state medical condition (3)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (3) Medical condition")
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state date of diagnosis (dd/mm/yyyy) (3)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (3) Diagnosis date (dd/mm/yyyy)")
        elif "Does the Life Assured have any other medical conditions? If \"YES\", please state name & address of treating doctor (1)" in name:
            set_field_with_confidence(field, combined, "Medical conditions, date of diagnosis, name & address of treating doctor (rows 0..3) (3) Name & address of treating doctor")

        elif "Does the Life Assured have any other medical conditions?" in name:
            set_delete_with_confidence(field, combined, "Does Life Assured have any other medical conditions?")

        elif "Does the Life Assured have any family history? If \"Yes\", please provide details of the nature of condition (1)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (1) Family history condition")
        elif "Does the Life Assured have any family history? If \"Yes\", please provide details including relationship to the Life Assured (1)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (1) Relationship to Life Assured")
        elif "Does the Life Assured have any family history? If \"Yes\", please provide details of the age of onset (1)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (1) Age of onset")

        elif "Does the Life Assured have any family history? If \"Yes\", please provide details of the nature of condition (2)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (2) Family history condition")
        elif "Does the Life Assured have any family history? If \"Yes\", please provide details including relationship to the Life Assured (2)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (2) Relationship to Life Assured")
        elif "Does the Life Assured have any family history? If \"Yes\", please provide details of the age of onset (2)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (2) Age of onset")

        elif "Does the Life Assured have any family history? If \"Yes\", please provide details of the nature of condition (3)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (3) Family history condition")
        elif "Does the Life Assured have any family history? If \"Yes\", please provide details including relationship to the Life Assured (3)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (3) Relationship to Life Assured")
        elif "Does the Life Assured have any family history? If \"Yes\", please provide details of the age of onset (3)" in name:
            set_field_with_confidence(field, combined, "Family History (rows 0..3) (3) Age of onset")

        elif "Does the Life Assured have any family history?" in name:
            set_delete_with_confidence(field, combined, "Does Life Assured have any family history?")

        elif "Please give details of the Life Assured's habits in relation to cigarette smoking, including the duration of smoking habit, number of cigarettes smoked per day and source of information" in name:
            set_field_with_confidence(field, combined, "Details of the Life Assured’s habits in relation to cigarette smoking, including the duration of smoking habit, number of cigarettes smoked per day and source of information")

        elif "Please give details of the Life Assured's habit in relation to alcohol consumption including the amount of alcohol consumption per day and source of information" in name:
            set_field_with_confidence(field, combined, "Details of the Life Assured’s habit in relation to alcohol consumption including the amount of alcohol consumption per day and source of information")

        elif "Please provide any other information which may be of assistance to us in assessing this claim" in name:
            set_field_with_confidence(field, combined, "Please provide any other information which may be of assistance to us in assessing this claim")

        # --- Default for unmapped fields ---
        else:
            field["field_value"] = ""
            field["confidence"] = ""

    return form_fields

# --- Run ---
if __name__ == "__main__":
    file_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "sample" / "cleaned-llm-output.json"
    with open(file_path, "r", encoding="utf-8") as f:
        cleaned_llm_output = f.read()
    
    # Choose either "ntuc" or "ge"
    template_choice = "ge"
    if template_choice == "ge":
        with open("ge_form_fields_empty.json") as f:
            form_fields = json.load(f)
        
        fill_pdf_json = map_combined_to_fields_ge(cleaned_llm_output, form_fields)

    if template_choice == "ntuc":
        with open("ntuc_form_fields_empty.json") as f:
            form_fields = json.load(f)
        
        fill_pdf_json = map_combined_to_fields_ge(cleaned_llm_output, form_fields)
    
    filled_file_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "sample" / "form_fields_filled.json"

    with open(filled_file_path, "w") as f:
        json.dump(fill_pdf_json, f, indent=4, ensure_ascii=False)