# llm.py

# ---- Pull LLM from ollama first (if done locally) ----
# run commands below in terminal
# !apt-get update
# !apt-get install -y curl
# !curl -fsSL https://ollama.com/install.sh | sh

# !ollama serve > /dev/null 2>&1 &

# !ollama pull phi4

import yaml
import json
import requests
from pathlib import Path
import concurrent.futures

# --- PROMPT BUILDER ---

def build_prompt(i_txt: str, page_num: int, field_json_schemas: dict, meta_rules: str) -> str:

    """Constructs the full LLM prompt from retrieved text and schema."""
    system = meta_rules.strip()
    schema = field_json_schemas.get(page_num, {})

    user = f"""
You are given the retrieval results from RAG, where it details the most relevant sections of doctor's records for a specific patient in Singapore. They are excerpts from different sections found in the appointment notes with relevant dates and information:

RETRIEVED TEXT:
<<<
{i_txt}
>>>

Task:
- Fill the JSON schema below using ONLY information from the notes, and also include the confidence score which should reflect probability that YOUR answer is correct.
- If no information exists, output "".
- Try your best to fill in the JSON as completely as possible, even if it is not accurate (you may give it a low confidence score).
- Return JSON only.

Remember, return ONLY valid JSON. DO NOT include markdown, comments, or explanations. No comments at all.

JSON schema:
{schema}
""".strip()

    return f"{system}\n\n{user}"

# query phi4 model
def query_ollama(prompt: str) -> str:
    OLLAMA_URL = "http://localhost:11434/api/generate"

    payload = {"model": "phi4", "prompt": prompt}
    output = ""
    with requests.post(OLLAMA_URL, json=payload, stream=True) as r:
        for line in r.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                if "response" in data:
                    output += data["response"]
    return output

def query_page(i, i_text, field_json_schema):
    prompt = build_prompt(i_text, i, field_json_schema)
    response = query_ollama(prompt)
    return i, f"\n--- Page {i} ---\n{response}"

def run_all(all_retrieval_results, n_pages, field_json_schema, use_multithreading=True):
    results = {}
    if use_multithreading:
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_pages) as executor:
            futures = []
            for i in range(1, n_pages + 1):
                i_text = all_retrieval_results[i]["aggregated_text"]
                futures.append(executor.submit(query_page, i, i_text, field_json_schema))
            for f in concurrent.futures.as_completed(futures):
                i, output = f.result()
                results[i] = output
    else:
        for i in range(1, n_pages + 1):
            i_text = all_retrieval_results[i]["aggregated_text"]
            i, output = query_page(i, i_text, field_json_schema)
            results[i] = output
    return results

if __name__ == "__main__":
    # --- Load configuration ---
    with open("llm-config.yml", 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
        llm_prompts = config.get('llm_prompts', {})

    # Choose either "ntuc_prompts" or "ge_prompts"
    template_choice = "ntuc_prompts"

    META_RULES = llm_prompts.get('meta_rules')
    schema = {}

    prompt_set = llm_prompts.get(template_choice, {})

    if not prompt_set:
        pass

    temp_schema = {}

    for key, path_from_config in prompt_set.items():
        
        if key.startswith("page_"):
            page_number = int(key.split('_')[1])
            
            with open(path_from_config, 'r', encoding='utf-8') as f:
                content = f.read()
            
            temp_schema[page_number] = content

    schema = dict(sorted(temp_schema.items()))
    n_pages = len(schema)

    # define retrievel results
    json_file_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "sample" / "retrieval.json"

    with open(json_file_path, 'r', encoding='utf-8') as f:
        all_retrieval_results = json.load(f)

    results = run_all(all_retrieval_results, n_pages, schema)

    final_results = "\n".join([results[i] for i in sorted(results.keys())])
    output_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "sample" / "llm-output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_results)