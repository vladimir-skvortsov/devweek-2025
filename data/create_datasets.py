import os
import uuid
import pandas as pd
from dotenv import load_dotenv

from providers import KaggleProvider, HuggingFaceProvider

load_dotenv()

if os.getenv('KAGGLE_USERNAME') and os.getenv('KAGGLE_KEY'):
    os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME')
    os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY')

datasets = [
    # Kaggle datasets
    KaggleProvider(
        'sunilthite/llm-detect-ai-generated-text-dataset',
        lambda df: df[['text', 'generated']].assign(
            is_human=lambda x: 1 - x['generated'], id=lambda x: [uuid.uuid4().hex for _ in range(len(x))]
        )[['id', 'text', 'is_human']],
    ),
    KaggleProvider(
        'prajwaldongre/llm-detect-ai-generated-vs-student-generated-text',
        lambda df: df[['Text', 'Label']].assign(
            is_human=lambda x: (x['Label'] == 'student').astype('int64'),
            text=lambda x: x['Text'],
            id=lambda x: [uuid.uuid4().hex for _ in range(len(x))],
        )[['id', 'text', 'is_human']],
    ),
    KaggleProvider(
        'thedrcat/daigt-v4-train-dataset',
        lambda df: df[['text', 'label']].assign(
            is_human=lambda x: 1 - x['label'], id=lambda x: [uuid.uuid4().hex for _ in range(len(x))]
        )[['id', 'text', 'is_human']],
    ),
    KaggleProvider(
        'carlmcbrideellis/llm-7-prompt-training-dataset',
        lambda df: df[['text', 'label']].assign(
            is_human=lambda x: 1 - x['label'], id=lambda x: [uuid.uuid4().hex for _ in range(len(x))]
        )[['id', 'text', 'is_human']],
    ),
    # HuggingFace datasets
    HuggingFaceProvider(
        'shahxeebhassan/human_vs_ai_sentences',
        lambda df: df.assign(is_human=lambda x: 1 - x['label'], id=lambda x: [uuid.uuid4().hex for _ in range(len(x))])[
            ['id', 'text', 'is_human']
        ],
    ),
    HuggingFaceProvider(
        'ardavey/human-ai-generated-text',
        lambda df: df.assign(is_human=lambda x: 1 - x['label'], id=lambda x: [uuid.uuid4().hex for _ in range(len(x))])[
            ['id', 'text', 'is_human']
        ],
    ),
]

datasets_df = [dataset.get_df() for dataset in datasets]
merged_df = pd.concat(datasets_df)

SAMPLE_SIZE = 100
share = SAMPLE_SIZE // len(datasets_df)
remainder = SAMPLE_SIZE - share * len(datasets_df)

samples_df = []
for i, sample_df in enumerate(datasets_df):
    n = share + (1 if i < remainder else 0)
    samples_df.append(sample_df.sample(n=n, random_state=0))

sample_df = pd.concat(samples_df)

merged_df.to_csv('merged.csv', index=False)
sample_df.to_csv('merged_sample.csv', index=False)

print(len(merged_df), len(sample_df))
