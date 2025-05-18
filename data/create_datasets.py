from datasets import load_dataset, concatenate_datasets, Value, Dataset


def load_hf(repo: str) -> Dataset:
    ds = load_dataset(repo, split="train")
    ds = (
        ds.cast_column("label", Value("int64"))
          .map(lambda ex: {"is_human": 1 - ex["label"], "id": uuid.uuid4().hex})
    )
    keep = {"id", "text", "is_human"}
    return ds.remove_columns([c for c in ds.column_names if c not in keep])

# Грузим HF
ds_hf1 = load_hf("shahxeebhassan/human_vs_ai_sentences")
ds_hf2 = load_hf("ardavey/human-ai-generated-text")

# Грузим Kaggle
csv_path = pathlib.Path(__file__).with_name("training_essay_data.csv")
ds_csv = (
    load_dataset("csv", data_files=str(csv_path), split="train")
      .cast_column("is_human", Value("int64"))
      .map(lambda _: {"id": uuid.uuid4().hex})
)

keep = {"id", "text", "is_human"}
ds_csv = ds_csv.remove_columns([c for c in ds_csv.column_names if c not in keep])

# Full dataset
full_ds = concatenate_datasets([ds_hf1, ds_hf2, ds_csv])

# Mini dataset 1000
TARGET = 1_000
parts   = [ds_hf1, ds_hf2, ds_csv]
share   = TARGET // len(parts)
remainder = TARGET - share * len(parts)

samples = []
for i, ds in enumerate(parts):
    n = share + (1 if i < remainder else 0)   # 333/333/334
    samples.append(ds.shuffle(seed=42).select(range(n)))

mini_ds = concatenate_datasets(samples)

#print(f"full_ds rows: {len(full_ds):,}")
#print(f"mini_ds rows: {len(mini_ds):,} "
#      f"({len(samples[0])}/{len(samples[1])}/{len(samples[2])})\n")

#print(mini_ds.to_pandas().head(100))