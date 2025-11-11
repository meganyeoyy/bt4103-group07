import json

# Input and output file paths
input_file = "combined.json"   # replace with your actual file name
output_file = "dummy_data.json"

# Load JSON from file
with open(input_file, "r") as f:
    data = json.load(f)

# Clear all values (set everything to empty string)
cleared_data = {k: "" for k in data.keys()}

# Save cleared JSON to a new file
with open(output_file, "w") as f:
    json.dump(cleared_data, f, indent=4)

print(f"Cleared JSON saved to {output_file}")
