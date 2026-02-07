from pathlib import Path
import json
import pandas as pd
from sklearn.model_selection import train_test_split

base_dir = Path(__file__).resolve().parent.parent
data_path = base_dir / "data" / "all_pairs_data.json"

with open(data_path) as f:
    data = json.load(f)

acid_pairs = pd.DataFrame(data["acids"])
base_pairs = pd.DataFrame(data["bases"])
amp_pka_pairs = pd.DataFrame(data["amphoterics_pka"])
amp_pkah_pairs = pd.DataFrame(data["amphoterics_pkah"])

def sampling(df):
    df_sampled, _ = train_test_split(df, train_size=0.1, stratify=df['functional_group'], random_state=42)
    return df_sampled

acid_pairs_sample = sampling(acid_pairs)
base_pairs_sample = sampling(base_pairs)
amp_pka_pairs_sample = sampling(amp_pka_pairs)
amp_pkah_pairs_sample = sampling(amp_pkah_pairs)

sample_pairs = {
    'acids': acid_pairs_sample.to_dict(orient='records'),
    'bases': base_pairs_sample.to_dict(orient='records'),
    'amphoterics_pka': amp_pka_pairs_sample.to_dict(orient='records'),
    'amphoterics_pkah': amp_pkah_pairs_sample.to_dict(orient='records')
}

with open(base_dir / "sample" / "sample_pairs.json", 'w') as f:
    json.dump(sample_pairs, f, indent=4)


