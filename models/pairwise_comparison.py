import json
import random
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import os

# Config
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
DATA_FILE = "sample/sample_pairs.json"
OUTPUT_FILE = "results/phase1_results_raw.jsonlist"

# Set to None to run the full dataset
SAMPLE_SIZE = None


SYSTEM_CONTENT = "You are an expert in Physical Organic Chemistry."

ACID_USER_TEMPLATE = """I have two substances labeled A and B.

Substance A: {smiles_A}
Substance B: {smiles_B}

## Task
Compare the acid strength of these two substances by considering their acidity (pKa).

## Instructions
1. Think step-by-step to derive which substance is the stronger acid.
2. Provide your final decision in the strict format below.
3: Assume standard conditions (25°C and aqueous solution).
4. Start your answer with: "[Answer]: Substance A/B" (whichever is the stronger acid).

## Response Format
[Answer]: Substance A OR Substance B
[Analysis]: ... your step-by-step reasoning ..."""

BASE_USER_TEMPLATE = """I have two substances labeled A and B.

Substance A: {smiles_A}
Substance B: {smiles_B}

## Task
Compare the base strength of these two substances by considering the acidity (pKaH) of their conjugate acids.

## Instructions
1. Think step-by-step to derive which substance is the stronger base.
2. Provide your final decision in the strict format below.
3: Assume standard conditions (25°C and aqueous solution).
4. Start your answer with: "[Answer]: Substance A/B" (whichever is the stronger base).

## Response Format
[Answer]: Substance A OR Substance B
[Analysis]: ... your step-by-step reasoning ..."""

# Model loader
def load_model():    
    # Load Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    # Load Model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map="cpu",          # Force CPU
        torch_dtype=torch.float32  # Safe precision
    )
    return model, tokenizer

# Inference/Generation
def run_inference(model, tokenizer, messages):
    """
    Applies the correct chat template (System/User roles) and generates response.
    """
    # Convert message list to the model's specific string format (e.g. [INST]...[/INST])
    input_ids = tokenizer.apply_chat_template(
        messages, 
        return_tensors="pt", 
        add_generation_prompt=True
    )

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            input_ids, 
            max_new_tokens=32, 
            temperature=0.0, # Deterministic
            do_sample=False, # Ensures the most likely token is always picked (reproducibility)
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode: slicing off the prompt
    response = tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
    return response

# MAIN
def main():
    # Load previous
    processed_signatures = set()
    
    if os.path.exists(OUTPUT_FILE):
        print(f"Existing progress: {OUTPUT_FILE}")
        try:
            with open(OUTPUT_FILE, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        # Create a unique signature: (SMILES_A, SMILES_B, Category)
                        sig = (entry['smiles_A'], entry['smiles_B'], entry['category'])
                        processed_signatures.add(sig)
                    except json.JSONDecodeError:
                        continue
            print(f"[RESUMING]: Found {len(processed_signatures)} pairs already processed.")
        except Exception as e:
            print(f"[WARNING]: Could not read output file: {e}")


    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("[ERROR]: Data file not found.")
        return

    task_queue = []
    
    # Acid prompt
    for cat in ['acids', 'amphoterics_pka']:
        if cat in data:
            for entry in data[cat]:
                entry['prompt_type'] = 'ACID'
                task_queue.append(entry)
    
    # Base prompt
    for cat in ['bases', 'amphoterics_pkah']:
        if cat in data:
            for entry in data[cat]:
                entry['prompt_type'] = 'BASE'
                task_queue.append(entry)

    total_pairs = len(task_queue)
    print(f"Total pairs in dataset: {total_pairs}")

    # Sampling
    if SAMPLE_SIZE and SAMPLE_SIZE < total_pairs:
        print(f"Sampling {SAMPLE_SIZE} pairs for this test run...")
        task_queue = random.sample(task_queue, SAMPLE_SIZE)
    

    model, tokenizer = load_model()
    
    results = []
    pairs_skipped = 0

    # return

    for i, entry in enumerate(task_queue):
        s1 = entry['SMILES1']
        s2 = entry['SMILES2']
        ptype = entry['prompt_type']

        # CHECK IF PROCESSED
        sig = (s1, s2, ptype)
        if sig in processed_signatures:
            pairs_skipped += 1
            # Optional: Print status every 100 skips just so you know it's working
            if pairs_skipped % 1000 == 0:
                print(f"Skipping {pairs_skipped} pairs...", end="\r")
            continue

        
        # Build message structures
        # Create a list of dictionaries.
        # This allows the Tokenizer to handle the specific formatting for Mistral/Llama/etc.
        
        if ptype == 'ACID':
            user_content = ACID_USER_TEMPLATE.format(smiles_A=s1, smiles_B=s2)
        else:
            user_content = BASE_USER_TEMPLATE.format(smiles_A=s1, smiles_B=s2)

        messages = [
            {"role": "system", "content": SYSTEM_CONTENT},
            {"role": "user", "content": user_content}
        ]

        print(f"Processing {i}/{len(task_queue)}...", flush=True)

        # Run LLM
        response = run_inference(model, tokenizer, messages)
        
        # Create Result Object
        result_entry = {
            "smiles_A": s1,
            "smiles_B": s2,
            "category": ptype,
            "ground_truth_pka_A": entry.get('pka(h)_value1'),
            "ground_truth_pka_B": entry.get('pka(h)_value2'),
            "full_prompt": user_content, # full prompt
            "raw_response": response     # full output
        }

        print(response)

        # **Append** immediately to jsonlist
        with open(OUTPUT_FILE, 'a') as f:
            f.write(json.dumps(result_entry) + "\n")
    
if __name__ == "__main__":
    main()

# nohup ./venv/bin/python3 -u pairwise_comparison.py > execution_log.txt 2>&1 &