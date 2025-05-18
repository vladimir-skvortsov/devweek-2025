import os
from dotenv import load_dotenv
import kagglehub
import pandas as pd
import uuid
import pathlib
from datasets import load_dataset, concatenate_datasets, Value, Dataset


def load_hf(repo: str) -> Dataset:
    ds = load_dataset(repo, split='train')
    ds = ds.cast_column('label', Value('int64')).map(lambda ex: {'is_human': 1 - ex['label'], 'id': uuid.uuid4().hex})
    keep = {'id', 'text', 'is_human'}
    return ds.remove_columns([c for c in ds.column_names if c not in keep])


def load_kaggle_as_hf() -> Dataset:
    load_dotenv()
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        os.environ["KAGGLE_USERNAME"] = os.getenv("KAGGLE_USERNAME")
        os.environ["KAGGLE_KEY"] = os.getenv("KAGGLE_KEY")

    path = kagglehub.dataset_download("sunilthite/llm-detect-ai-generated-text-dataset")
    print("Path to dataset files:", path)
    files = os.listdir(path)
    print("Files in dataset folder:", files)
    csv_files = [f for f in files if f.endswith('.csv')]
    if not csv_files:
        raise Exception("There are no csv files in the folder")
    kaggle_df = pd.read_csv(os.path.join(path, csv_files[0]))

    if 'text' not in kaggle_df.columns or 'generated' not in kaggle_df.columns:
        raise Exception(f"Fields were expected text and generated, but actually: {kaggle_df.columns}")

    kaggle_df = kaggle_df[['text', 'generated']].copy()
    kaggle_df['is_human'] = 1 - kaggle_df['generated']
    kaggle_df['id'] = [uuid.uuid4().hex for _ in range(len(kaggle_df))]
    kaggle_df = kaggle_df[['id', 'text', 'is_human']]

    ds_kaggle = Dataset.from_pandas(kaggle_df, preserve_index=False)
    return ds_kaggle

# Грузим HF
ds_hf1 = load_hf('shahxeebhassan/human_vs_ai_sentences')
ds_hf2 = load_hf('ardavey/human-ai-generated-text')

# Грузим Kaggle
ds_csv = load_kaggle_as_hf()

# Full dataset
full_ds = concatenate_datasets([ds_hf1, ds_hf2, ds_csv])

output_path = pathlib.Path(__file__).with_name('merged.csv')
full_ds.to_csv(output_path, index=False)

# Mini dataset 1000
TARGET = 100
parts = [ds_hf1, ds_hf2, ds_csv]
share = TARGET // len(parts)
remainder = TARGET - share * len(parts)

samples = []
for i, ds in enumerate(parts):
    n = share + (1 if i < remainder else 0)  # 333/333/334
    print(n)
    samples.append(ds.shuffle(seed=42).select(range(n)))

mini_ds = concatenate_datasets(samples)

# Save mini dataset
output_path = pathlib.Path(__file__).with_name('merged_sample.csv')
mini_ds.to_csv(output_path, index=False)
