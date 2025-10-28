import json
import re
import torch
from sklearn.metrics import f1_score
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

def get_embedding(text: str):
    if not text:
        return None
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        # Use mean pooling of token embeddings (excluding padding)
        attention_mask = inputs["attention_mask"]
        token_embeddings = outputs.last_hidden_state
        mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        summed = torch.sum(token_embeddings * mask_expanded, 1)
        counts = torch.clamp(mask_expanded.sum(1), min=1e-9)
        return summed / counts

def cosine_similarity(a, b):
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.0
    return torch.nn.functional.cosine_similarity(a, b).item()

# -------- Collapse Yes/No pairs --------
def load_fields(path):
    with open(path, "r") as f:
        data = json.load(f)

    return {
        f["field_name"]: {
            "field_type": f.get("field_type", "text"),
            "field_value": f.get("field_value", ""),
            "page": f.get("page", None)
        } for f in data["fields"]
    }

def collapse_yesno(fields: dict, base_name: str) -> str:
    """Collapse Yes/No checkbox pair into single logical value."""
    yes = fields.get(base_name + " Yes", {}).get("field_value", "").lower() == "yes"
    no  = fields.get(base_name + " No", {}).get("field_value", "").lower() == "yes"

    if yes and not no:
        return "Yes"
    elif no and not yes:
        return "No"
    else:
        return ""  # invalid or unanswered

def evaluate_files(gt_path, pred_path):
    
    gt_dict = load_fields(gt_path)
    pred_dict = load_fields(pred_path)
    results = []

    y_true, y_pred = [], []

    # collapse the yes/no variations of checkbox questions
    checkbox_questions = {
        fname.rsplit(" ", 1)[0]
        for fname, details in gt_dict.items()
        if details.get("field_type") == "checkbox"
    }

    # handling checkbox qns
    for qn in checkbox_questions:
        gt_yn = collapse_yesno(gt_dict, qn)
        if gt_yn == "":  # skip unanswered yn qn in gt
            continue

        pred_yn = collapse_yesno(pred_dict, qn)

        gt_binary = 1 if gt_yn == "Yes" else 0
        pred_binary = 1 if pred_yn == "Yes" else 0

        y_true.append(gt_binary)
        y_pred.append(pred_binary)

        results.append({
            "field_name": qn,
            "type": "checkbox",
            "ground_truth": gt_yn,
            "prediction": pred_yn,
        })


    # handling free_text qns
    for field_name, gt_field_details in gt_dict.items():
        if gt_field_details.get("field_type", "text") == "checkbox":
            continue
        else:
            gt_text = gt_field_details.get("field_value", "")

            if not gt_text or not gt_text.strip():  # only score when GT has value
                continue
            
            pred_field_details = pred_dict.get(field_name, {})
            pred_text = pred_field_details.get("field_value", "")


            similarity = cosine_similarity(get_embedding(gt_text), get_embedding(pred_text))

            results.append({
                "field_name": field_name,
                "type": "text",
                "ground_truth": gt_text,
                "prediction": pred_text,
                "similarity": similarity
        })


    return results, y_true, y_pred

if __name__ == "__main__":
    gt_path = "data/eval/ntuc_gt_patient_1.json"
    pred_path = "data/eval/ntuc_norag_patient_1.json"


    # Strip everything before and including "eval/"
    gt_name = gt_path.split("eval/")[-1]
    pred_name = pred_path.split("eval/")[-1]

    eval_results, y_true, y_pred = evaluate_files(gt_path, pred_path)

    for row in eval_results:
        print(row)

    f1 = f1_score(y_true, y_pred)

    sim_scores = [r["similarity"] for r in eval_results if r["type"] == "text"]
    avg_similarity = sum(sim_scores) / len(sim_scores) if sim_scores else 0.0


    print(f"Evaluating:\n GT:   {gt_name}\n Pred: {pred_name}\n")
    print("\n--- Aggregate Results---")
    print(f"Overall F1 (Yes/No): {f1:.3f}")
    print(f"Average Similarity (Free text): {avg_similarity:.3f}")
