import json

input_path = "form_fields.json"   # your source file
output_path = "form_fields_empty.json" # file to save cleaned version

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# make sure we have "fields" array
if "fields" in data and isinstance(data["fields"], list):
    for field in data["fields"]:
        # reset value
        field["field_value"] = ""
        # ensure confidence always exists
        field["confidence"] = ""

# save back to new file
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"All field_value cleared and confidence ensured. Saved to {output_path}")