import re
import json

# script will clean the LLM output and also format it into a JSON suitable for processing
# might need to change path structure depending on data filing

file_path = "../../../data/raw-txt/llm_output.txt"
cleaned_path = "../../../data/json/cleaned_output.txt"
output_path = "combined.json"

def clean_llm_output(text: str) -> str:
    text = re.sub(r"--- Page \d+ ---", "", text)
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    # remove common "trailing commas" 
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # collapse multiple tabs/spaces
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def extract_json_objects(text: str):
    """Extract top-level {...} objects while respecting strings and escapes."""
    objs = []
    n = len(text)
    i = 0
    in_str = False
    escape = False
    depth = 0
    start = None
    while i < n:
        ch = text[i]
        if ch == '"' and not escape:
            in_str = not in_str
        if not in_str:
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(text[start:i+1])
                    start = None
        # handle escape char
        if ch == "\\" and not escape:
            escape = True
        else:
            escape = False
        i += 1

    # if ended while still inside an object, attempt to close it
    if start is not None:
        tail = text[start:]
        # count unmatched braces/brackets and append closers
        opens = tail.count('{') - tail.count('}')
        opens_sq = tail.count('[') - tail.count(']')
        tail_fixed = tail + ('}' * opens) + (']' * opens_sq)
        objs.append(tail_fixed)
    return objs

def repair_json(s: str) -> str:
    # remove trailing commas like {"a":1,}
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # if there are unbalanced braces/brackets, append closers (defensive)
    open_curly = s.count('{') - s.count('}')
    open_sq = s.count('[') - s.count(']')
    if open_curly > 0:
        s = s + ('}' * open_curly)
    if open_sq > 0:
        s = s + (']' * open_sq)
    return s

def flatten_json(obj: dict, parent_key: str = "", sep: str = " ") -> dict:
    items = {}
    for k, v in obj.items():
        new_key = f"{parent_key}{sep}{k}".strip()
        if isinstance(v, dict):
            items.update(flatten_json(v, new_key, sep=sep))
        elif isinstance(v, list):
            # flatten list of dicts into numbered entries
            for idx, elem in enumerate(v, 1):
                if isinstance(elem, dict):
                    items.update(flatten_json(elem, f"{new_key} ({idx})", sep=sep))
                else:
                    items[f"{new_key} ({idx})"] = elem
        else:
            items[new_key] = v
    return items

# read + clean
with open(file_path, "r", encoding="utf-8") as f:
    raw = f.read()

cleaned = clean_llm_output(raw)
with open(cleaned_path, "w", encoding="utf-8") as f:
    f.write(cleaned)

# Extract objects robustly
json_chunks = extract_json_objects(cleaned)

merged = {}
all_keys = set()
for i, chunk in enumerate(json_chunks, 1):
    fixed = repair_json(chunk)
    try:
        obj = json.loads(fixed)
    except json.JSONDecodeError as e:
        # try to remove trailing non-json prefix/suffix and parse
        try:
            # strip any leading/trailing characters before first { and after last }
            first = fixed.find('{')
            last = fixed.rfind('}')
            if first != -1 and last != -1 and last > first:
                candidate = fixed[first:last+1]
                candidate = repair_json(candidate)
                obj = json.loads(candidate)
            else:
                raise
        except Exception as e2:
            print(f"[SKIP] chunk {i} UNRECOVERABLE: {e2}")
            print("---- preview ----")
            print(chunk[:500])
            print("--------------")
            continue

    # flatten and merge
    flat = flatten_json(obj)
    # log parsed keys for debugging (so you can see if those diagnosis keys exist)
    if flat:
        print(f"[OK] chunk {i} parsed keys: {list(flat.keys())[:10]}{'...' if len(flat)>10 else ''}")
    else:
        print(f"[OK] chunk {i} parsed no top-level keys")

    merged.update(flat)
    all_keys.update(flat.keys())

# save
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=4, ensure_ascii=False)

print(f"Combined keys: {len(all_keys)} saved to {output_path}")
