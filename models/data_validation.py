import json
import sys

def validate_dataset(file_path):
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("[ERROR]: File not found.")
        return
    except json.JSONDecodeError:
        print("[ERROR]: Invalid JSON format.")
        return

    # Maps SMILES Key -> The category it belongs to
    key_to_category = {
        'acids': 'ACID',
        'bases': 'BASE',
        'amphoterics_pka': 'AMPHOTERIC',
        'amphoterics_pkah': 'AMPHOTERIC'
    }

    substance_tracker = {} 
    
    # Maps Normalized Pair Tuple -> JSON Key where it was found
    pair_tracker = {}

    # ERROR COUNTERS
    errors = {
        'substance_overlap': 0,
        'duplicate_pairs': 0,
        'self_pairs': 0
    }

    # Iterate through the keys (in json)
    for json_key, logical_cat in key_to_category.items():
        if json_key not in data:
            print(f"[WARNING]: Key '{json_key}' not found in JSON.")
            continue
            
        entries = data[json_key]

        for i, entry in enumerate(entries):
            s1 = entry.get('SMILES1')
            s2 = entry.get('SMILES2')

            if not s1 or not s2:
                continue

            # RULE 1: Substance Exclusivity
            # A substance cannot exist in ACID and BASE, or ACID and AMPHOTERIC.
            
            for substance in [s1, s2]:
                if substance in substance_tracker:
                    existing_cat = substance_tracker[substance]
                    
                    # If the existing category is different from the current one, it's an error.
                    # Note: If existing is AMPHOTERIC and current is AMPHOTERIC (e.g. from pka vs pkah), that is OK.
                    if existing_cat != logical_cat:
                        errors['substance_overlap'] += 1
                else:
                    # First time seeing this substance, register it
                    substance_tracker[substance] = logical_cat

            # RULE 2: Pair Uniqueness
            # Pair (A, B) must be unique within its specific list context.
            # (A, B) is treated identical to (B, A).
            # Amphoterics: (A,B) can exist in 'amphoterics_pka' AND 'amphoterics_pkah',
            # but cannot exist twice within 'amphoterics_pka'.

            if s1 == s2:
                errors['self_pairs'] += 1
                continue

            # Sort to normalize order: (A, B) == (B, A)
            sorted_pair = tuple(sorted((s1, s2)))

            # Composite key that includes the json_key (the specific list name).
            # This allows the same pair to exist in 'amphoterics_pka' and 'amphoterics_pkah',
            unique_pair_entry = (sorted_pair, json_key)

            if unique_pair_entry in pair_tracker:
                errors['duplicate_pairs'] += 1
            else:
                pair_tracker[unique_pair_entry] = f"{json_key} (Index {i})"

    # FINAL REPORT
    print(f"Total number of pairs:    {len(pair_tracker)}")
    print(f"Substance Overlap Errors: {errors['substance_overlap']}")
    print(f"Duplicate Pair Errors:    {errors['duplicate_pairs']}")
    print(f"Self-Pair Errors:         {errors['self_pairs']}")
    
    if sum(errors.values()) == 0:
        print("[PASSED]")
    
# MAIN
validate_dataset('data/all_pairs_data.json')