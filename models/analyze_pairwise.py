import json
import re
from collections import defaultdict

# CONFIGURATION
GROUND_TRUTH_FILE = "sample/sample_pairs.json" 
RESULTS_FILE = "results/phase1_results_gpt.jsonlist"

# 1. LOAD GROUND TRUTH METADATA
def load_ground_truth(filepath):
    """
    Creates a lookup map to retrieve the specific category (e.g., 'acids', 'bases')
    and functional group for any given pair of SMILES.
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR]: Could not find {filepath}")
        return {}

    # Map keys: (SMILES_A, SMILES_B) -> { 'group': 'acids', 'fg': 'CO2H' }
    gt_map = {}
    
    # We look through all 4 specific categories
    categories = ['acids', 'bases', 'amphoterics_pka', 'amphoterics_pkah']
    
    count = 0
    for cat in categories:
        if cat not in data: continue
        for entry in data[cat]:
            s1 = entry['SMILES1']
            s2 = entry['SMILES2']
            fg = entry.get('functional_group', 'Unknown')
            
            # Store using tuple key
            gt_map[(s1, s2)] = {'group': cat, 'fg': fg}
            count += 1
            
    print(f"Loaded metadata for {count} pairs.")
    return gt_map

# 2. PARSE AND EVALUATE
def evaluate_results(results_path, gt_map):

    # Statistics Containers
    # Format: stats['metric_name'] = {'correct': 0, 'total': 0}
    stats_overall = {'correct': 0, 'total': 0}
    stats_groups = defaultdict(lambda: {'correct': 0, 'total': 0})
    stats_fg = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    parsing_errors = 0
    
    try:
        with open(results_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[ERROR]: Could not find {results_path}")
        return

    print(f"[Processing]: {len(lines)} results\n")

    for line in lines:
        if not line.strip(): continue
        entry = json.loads(line)
        
        s1 = entry['smiles_A']
        s2 = entry['smiles_B']
        prompt_type = entry['category'] # 'ACID' or 'BASE'
        raw_response = entry['raw_response']
        
        # 1. Retrieve Metadata
        meta = gt_map.get((s1, s2))
        if not meta:
            # Fallback check (in case A/B were swapped in storage, though unlikely based on script)
            meta = gt_map.get((s2, s1))
            
        if not meta:
            # If still not found, skip (or log warning)
            print("[WARNING]: Cannot find this pair")
            continue
            
        specific_group = meta['group'] # e.g., 'amphoterics_pka'
        func_group = meta['fg']        # e.g., 'PHENOL'

        # 2. Determine Correct Answer (Ground Truth)
        pka_A = entry['ground_truth_pka_A']
        pka_B = entry['ground_truth_pka_B']
        
        correct_label = None
        
        if prompt_type == 'ACID':
            # Task: "Stronger Acid" -> Lower pKa
            if pka_A < pka_B:
                correct_label = 'A'
            else:
                correct_label = 'B'
        elif prompt_type == 'BASE':
            # Task: "Stronger Base" -> Higher pKaH
            if pka_A > pka_B:
                correct_label = 'A'
            else:
                correct_label = 'B'
        
        # 3. Parse LLM Answer (Regex)
        # Regex 1: Standard format -> [Answer]: Substance A
        match = re.search(r"\[Answer\]:\s*Substance\s*([AB])", raw_response, re.IGNORECASE)
        
        # Regex 2 (Fallback): Markdown Header -> ## Answer: Substance A
        if not match:
            match = re.search(r"##\s*Answer:?\s*Substance\s*([AB])", raw_response, re.IGNORECASE)
        
        if match:
            predicted_label = match.group(1).upper() # 'A' or 'B'
            
            # Check correctness
            is_correct = (predicted_label == correct_label)
            
            # Update Counters (Correct or Incorrect)
            # Overall
            stats_overall['total'] += 1
            if is_correct: stats_overall['correct'] += 1
            
            # Per Group
            stats_groups[specific_group]['total'] += 1
            if is_correct: stats_groups[specific_group]['correct'] += 1
            
            # Per Functional Group
            stats_fg[func_group]['total'] += 1
            if is_correct: stats_fg[func_group]['correct'] += 1
            
        else:
            # CASE: PARSING FAILED
            parsing_errors += 1
            
            # Count as incorrect
            stats_overall['total'] += 1
            stats_groups[specific_group]['total'] += 1
            stats_fg[func_group]['total'] += 1
            
            # Print failure
            print(f"[PARSE ERROR]: Could not extract from:\n{raw_response[:300]}\n{'-'*30}")

    return stats_overall, stats_groups, stats_fg, parsing_errors

# 3. PRINT REPORT
def print_stats(title, data_dict):
    print(f"\n=== {title} ===")
    print(f"{'Category':<25} | {'Acc %':<8} | {'Fraction':<10}")
    print("-" * 48)
    
    # Sort by accuracy for nicer viewing
    sorted_items = sorted(data_dict.items(), key=lambda x: x[0])
    
    for name, stat in sorted_items:
        if stat['total'] == 0:
            acc = 0.0
        else:
            acc = (stat['correct'] / stat['total']) * 100
            
        print(f"{name:<25} | {acc:6.2f}% | {stat['correct']}/{stat['total']}")

# MAIN
if __name__ == "__main__":
    # 1. Load Map
    gt_map = load_ground_truth(GROUND_TRUTH_FILE)
    
    if gt_map:
        # 2. Evaluate
        overall, groups, fgs, errors = evaluate_results(RESULTS_FILE, gt_map)
        
        # 3. Report
        print(f"\n[Parsing Errors] (Failed to follow format): {errors}")
        
        # Overall
        if overall['total'] > 0:
            acc = (overall['correct']/overall['total'])*100
            print(f"\n>>> OVERALL ACCURACY: {acc:.2f}% ({overall['correct']}/{overall['total']})")
        
        # Groups
        print_stats("Accuracy by Dataset Group", groups)
        
        # Functional Groups
        print_stats("Accuracy by Functional Group", fgs)