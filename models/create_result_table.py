import json
import re
import csv
import os
from collections import defaultdict

# Config
GROUND_TRUTH_FILE = "sample/sample_pairs.json"
MODELS = ["chemllm", "gemma", "gpt", "llama", "mistral", "qwen"]
INPUT_FILE_PATTERN = "results/phase1_results_{model}.jsonlist"
TABLE1_OUTPUT = "accuracy/accuracy_by_dataset_with_fracs.csv"
TABLE2_OUTPUT = "accuracy/accuracy_by_functional_group_with_fracs.csv"

# SET TO TRUE/FALSE
SHOW_FRACTION = True 

# Load (groundtruth) metadata
def load_ground_truth(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR]: Could not find {filepath}")
        return {}

    gt_map = {}
    categories = ['acids', 'bases', 'amphoterics_pka', 'amphoterics_pkah']
    
    count = 0
    for cat in categories:
        if cat not in data: continue
        for entry in data[cat]:
            s1 = entry['SMILES1']
            s2 = entry['SMILES2']
            fg = entry.get('functional_group', 'Unknown')
            gt_map[(s1, s2)] = {'group': cat, 'fg': fg}
            count += 1
            
    print(f"Loaded metadata for {count} pairs.")
    return gt_map

# Evaluate a single (model) file
def evaluate_model(model_name, gt_map):
    results_path = INPUT_FILE_PATTERN.format(model=model_name)
    
    stats_overall = {'correct': 0, 'total': 0}
    stats_groups = defaultdict(lambda: {'correct': 0, 'total': 0})
    stats_fg = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    if not os.path.exists(results_path):
        print(f"[SKIP]: File not found: {results_path}")
        return None

    with open(results_path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            entry = json.loads(line)
            
            s1, s2 = entry['smiles_A'], entry['smiles_B']
            prompt_type = entry['category']
            raw_response = entry['raw_response']
            
            meta = gt_map.get((s1, s2)) or gt_map.get((s2, s1))
            if not meta: continue
                
            specific_group = meta['group']
            func_group = meta['fg']

            # Ground Truth Logic
            pka_A, pka_B = entry['ground_truth_pka_A'], entry['ground_truth_pka_B']
            correct_label = 'A' if (prompt_type == 'ACID' and pka_A < pka_B) or (prompt_type == 'BASE' and pka_A > pka_B) else 'B'
            
            # Parsing
            match = re.search(r"\[Answer\]:\s*Substance\s*([AB])", raw_response, re.IGNORECASE)
            if not match:
                match = re.search(r"##\s*Answer:?\s*Substance\s*([AB])", raw_response, re.IGNORECASE)
            
            is_correct = False
            if match:
                predicted_label = match.group(1).upper()
                is_correct = (predicted_label == correct_label)
            
            # Update counters
            for d in [stats_overall, stats_groups[specific_group], stats_fg[func_group]]:
                d['total'] += 1
                if is_correct: d['correct'] += 1

    return {"overall": stats_overall, "groups": stats_groups, "fg": stats_fg}

# Format cell utility
def format_cell(stats_dict):
    if not stats_dict or stats_dict['total'] == 0:
        return "N/A"
    
    acc = (stats_dict['correct'] / stats_dict['total']) * 100
    if SHOW_FRACTION:
        return f"{acc:.2f}% ({stats_dict['correct']}/{stats_dict['total']})"
    return f"{acc:.2f}%"

# Export to csv
def export_csv(filename, row_keys, model_results, result_type, row_label="Category", include_overall=False):
    """
    row_keys: List of row names (dataset groups or functional groups)
    model_results: Dict mapping model name to their stats dict
    result_type: 'groups' or 'fg'
    """
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header: Category, chemllm, gemma, ...
        header = [row_label] + MODELS
        writer.writerow(header)
        
        # Data Rows
        for key in sorted(row_keys):
            row = [key]
            for model in MODELS:
                if model in model_results:
                    row.append(format_cell(model_results[model][result_type].get(key)))
                else:
                    row.append("N/A")
            writer.writerow(row)
            
        # Optional Overall Row
        if include_overall:
            row = ["OVERALL"]
            for model in MODELS:
                if model in model_results:
                    row.append(format_cell(model_results[model]["overall"]))
                else:
                    row.append("N/A")
            writer.writerow(row)

# MAIN
if __name__ == "__main__":
    gt_map = load_ground_truth(GROUND_TRUTH_FILE)
    if not gt_map:
        exit()

    all_model_data = {}
    all_groups = set()
    all_fgs = set()

    # Collect data for all models
    for model in MODELS:
        print(f"Processing model: {model}")
        res = evaluate_model(model, gt_map)
        if res:
            all_model_data[model] = res
            all_groups.update(res['groups'].keys())
            all_fgs.update(res['fg'].keys())

    # Table 1: Accuracy by Dataset group
    export_csv(TABLE1_OUTPUT, all_groups, all_model_data, "groups", "Dataset Group", include_overall=True)
    print(f"Saved Table 1 to {TABLE1_OUTPUT}")

    # Table 2: Accuracy by Functional group
    export_csv(TABLE2_OUTPUT, all_fgs, all_model_data, "fg", "Functional Group", include_overall=False)
    print(f"Saved Table 2 to {TABLE2_OUTPUT}")