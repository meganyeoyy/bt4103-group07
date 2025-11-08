import re
import json
from pathlib import Path

def process_llm_output(input_text: str) -> dict:
    """
    Cleans an LLM output text file and converts it into a single flattened JSON file.

    Args:
        input_text (str): raw LLM text.

    Returns:
        dict: The merged and flattened JSON object.
    """

    # --- Helpers ---
    def clean_llm_output(text: str) -> str:
        text = re.sub(r"--- Page \d+ ---", "", text)
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```", "", text)

        def _strip_comments(match):
            s = match.group(0)
            if s.startswith('"'):
                return s
            return re.sub(r"//.*", "", s)

        text = re.sub(r'"(?:\\.|[^"\\])*"|[^"\n]+', _strip_comments, text)
        text = re.sub(r",\s*([}\]])", r"\1", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        return text.strip()

    def extract_json_objects(text: str):
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
            if ch == "\\" and not escape:
                escape = True
            else:
                escape = False
            i += 1
        if start is not None:
            tail = text[start:]
            opens = tail.count('{') - tail.count('}')
            opens_sq = tail.count('[') - tail.count(']')
            tail_fixed = tail + ('}' * opens) + (']' * opens_sq)
            objs.append(tail_fixed)
        return objs

    def repair_json(s: str) -> str:
        s = re.sub(r",\s*([}\]])", r"\1", s)
        open_curly = s.count('{') - s.count('}')
        open_sq = s.count('[') - s.count(']')
        if open_curly > 0:
            s += '}' * open_curly
        if open_sq > 0:
            s += ']' * open_sq
        return s

    def flatten_json(obj: dict, parent_key: str = "", sep: str = " ") -> dict:
        items = {}
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}".strip()
            if isinstance(v, dict):
                items.update(flatten_json(v, new_key, sep=sep))
            elif isinstance(v, list):
                for idx, elem in enumerate(v, 1):
                    if isinstance(elem, dict):
                        items.update(flatten_json(elem, f"{new_key} ({idx})", sep=sep))
                    else:
                        items[f"{new_key} ({idx})"] = elem
            else:
                items[new_key] = v
        return items

    def fix_short_dates(data: dict) -> dict:
        """Detect and fix ddmmyy-style date strings by expanding to ddmmyyyy."""
        fixed = {}
        for k, v in data.items():
            if isinstance(v, str):
                # match exactly 6 digits (e.g., '101025' -> '10/10/25' style)
                if re.fullmatch(r"\d{6}", v):
                    dd, mm, yy = v[:2], v[2:4], v[4:]
                    v = f"{dd}{mm}20{yy}"  # add '20' before the year part
                # 'dd/mm/yy' format
                elif re.fullmatch(r"\d{2}/\d{2}/\d{2}", v):
                    dd, mm, yy = v.split("/")
                    v = f"{dd}/{mm}/20{yy}"
            fixed[k] = v
        return fixed
    # --- Read + clean ---
    cleaned = clean_llm_output(input_text)
    json_chunks = extract_json_objects(cleaned)

    merged = {}
    all_keys = set()

    for i, chunk in enumerate(json_chunks, 1):
        fixed = repair_json(chunk)
        try:
            obj = json.loads(fixed)
        except json.JSONDecodeError:
            try:
                first = fixed.find('{')
                last = fixed.rfind('}')
                if first != -1 and last != -1 and last > first:
                    candidate = repair_json(fixed[first:last+1])
                    obj = json.loads(candidate)
                else:
                    continue
            except Exception:
                continue

        flat = flatten_json(obj)
        merged.update(flat)
        all_keys.update(flat.keys())

    merged = fix_short_dates(merged)

    return merged

if __name__ == "__main__":
        file_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "sample" / "llm-output.json"
        with open(file_path, "r", encoding="utf-8") as f:
            llm_output = f.read()

        cleaned_llm_output = process_llm_output(llm_output)

        cleaned_llm_output_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "sample" / "cleaned-llm-output.json"

        with open(cleaned_llm_output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_llm_output, f, indent=4, ensure_ascii=False)