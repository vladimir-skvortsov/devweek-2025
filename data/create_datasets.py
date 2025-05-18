import os
from dotenv import load_dotenv
import kagglehub
import pandas as pd
import os
from dotenv import load_dotenv
import kagglehub
import pandas as pd
import uuid
import pathlib
from datasets import load_dataset, concatenate_datasets, Value, Dataset

load_dotenv()
if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
    os.environ["KAGGLE_USERNAME"] = os.getenv("KAGGLE_USERNAME")
    os.environ["KAGGLE_KEY"] = os.getenv("KAGGLE_KEY")

keep = {'id', 'text', 'is_human'}


def load_hf(repo: str) -> Dataset:
    ds = load_dataset(repo, split='train').cast_column('label', Value('int64')).map(
        lambda ex: {'is_human': 1 - ex['label'], 'id': uuid.uuid4().hex})

    return ds.remove_columns([c for c in ds.column_names if c not in keep])


hf_datasets = ['shahxeebhassan/human_vs_ai_sentences',
               'ardavey/human-ai-generated-text']

kaggle_datasets = [('sunilthite/llm-detect-ai-generated-text-dataset', lambda df: (df[['text', 'generated']]
                                                                                   .assign(is_human=lambda x: 1 - x['generated'],
                                                                                           id=lambda x: [uuid.uuid4().hex for _ in range(len(x))])
                                                                                   [['id', 'text', 'is_human']])),
                   ("prajwaldongre/llm-detect-ai-generated-vs-student-generated-text", lambda df: (df[['Text', 'Label']]
                                                                                                   .assign(is_human=lambda x: (x['Label'] == 'student').astype('int64'),
                                                                                                           text=lambda x: x['Text'],
                                                                                                           id=lambda x: [uuid.uuid4().hex for _ in range(len(x))])
                                                                                                   [['id', 'text', 'is_human']])),
                   ("thedrcat/daigt-v4-train-dataset", lambda df: (df[['text', 'label']]
                                                                   .assign(is_human=lambda x: 1 - x['label'],
                                                                           id=lambda x: [uuid.uuid4().hex for _ in range(len(x))])
                                                                   [['id', 'text', 'is_human']])),
                   ("carlmcbrideellis/llm-7-prompt-training-dataset", lambda df: (df[['text', 'label']]
                                                                                  .assign(is_human=lambda x: 1 - x['label'],
                                                                                          id=lambda x: [uuid.uuid4().hex for _ in range(len(x))])
                                                                                  [['id', 'text', 'is_human']])),
                   ]


def load_kaggle() -> Dataset:
    processed_datasets = []
    for dataset_name, preparation_func in kaggle_datasets:
        path = kagglehub.dataset_download(dataset_name)
        files = os.listdir(path)
        csv_files = [f for f in files if f.endswith('.csv')]
        if not csv_files:
            raise Exception("There are no csv files in the folder")
        kaggle_df = pd.read_csv(os.path.join(path, csv_files[0]))

        processed_df = preparation_func(kaggle_df)
        processed_datasets.append(Dataset.from_pandas(
            processed_df, preserve_index=False))
    return processed_datasets


ds_hf = [load_hf(hf_dataset) for hf_dataset in hf_datasets]
ds_kaggle = load_kaggle()

full_ds = concatenate_datasets([*ds_hf, *ds_kaggle])
full_df = full_ds.to_pandas()

full_df["text_clean"] = full_df["text"].str.replace(
    r'\s+', ' ', regex=True).str.strip()
full_df = full_df.drop_duplicates(subset=["text_clean"])
full_df = full_df.drop(columns=["text_clean"])

full_ds = Dataset.from_pandas(full_df, preserve_index=False)

output_path = pathlib.Path(__file__).with_name('merged.csv')
full_ds.to_csv(output_path, index=False)

# Mini dataset 1000
TARGET = 100
parts = [*ds_hf, *ds_kaggle]
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
