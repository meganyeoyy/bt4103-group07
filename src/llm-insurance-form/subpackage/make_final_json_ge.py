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

def map_combined_to_fields(combined, form_fields):
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
        elif "Has the Life Assured underwent other m ode of treatment? If \"Yes\", please state date of treatment (ddmmyyyy)" in name:
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
        elif "Is the Life Assured mentally incapacitated in accordance to the Mental Capacity Act (Chapter 177A of Singapore)? " in name:
            set_delete_with_confidence(field, combined, "Is Life Assured mentally incapacitated?")

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

with open("combined.json") as f:
    combined = json.load(f)
with open("GE_form_fields_empty.json") as f:
    form_fields = json.load(f)

updated = map_combined_to_fields(combined, form_fields)

with open("form_fields_filled.json", "w") as f:
    json.dump(updated, f, indent=4, ensure_ascii=False)

print("All form fields (with confidence) have been updated into form_fields_filled.json")
