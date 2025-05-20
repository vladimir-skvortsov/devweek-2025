import os
import uuid
import pandas as pd
import argparse
from dotenv import load_dotenv

from providers import KaggleProvider, HuggingFaceProvider, FileProvider, KaggleCompetitionProvider
from S3Client import S3Client

parser = argparse.ArgumentParser(
    prog='create dataset',
    description='Download datasets from kaggle, hf or own S3',
    epilog='Text at the bottom of help',
)

parser.add_argument(
    '-s',
    '--use-s3',
    action='store_true',
    help='Download from S3 (if omitted, downloads directly from Kaggle/HF)',
    default=False,
)
parser.add_argument('-u', '--upload-to-s3', action='store_true', help='Upload datasets to s3', default=False)

our_namespace = parser.parse_args()

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
    KaggleCompetitionProvider(
        'llm-detect-ai-generated-text',
        'train_essays.csv',
        lambda df: (
            df.assign(is_human=lambda x: 1 - x['generated'])
            .assign(text_clean=lambda x: x['text'].str.replace(r'\s+', ' ', regex=True).str.strip())
            .drop_duplicates(subset=['text_clean'])
            .drop(columns=['generated', 'text_clean'])[['id', 'text', 'is_human']]
        ),
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
    # Local datasets
    FileProvider(
        'raw/ruatd-2022-bi-train.csv',
        transform_func=lambda df: df.rename(columns={'Text': 'text'}).assign(
            is_human=lambda x: (x['Class'] == 'H').astype('int64'),
            id=lambda x: [uuid.uuid4().hex for _ in range(len(x))],
        )[['id', 'text', 'is_human']],
    ),
    FileProvider(
        'raw/ruatd-2022-bi-val.csv',
        transform_func=lambda df: df.rename(columns={'Text': 'text'}).assign(
            is_human=lambda x: (x['Class'] == 'H').astype('int64'),
            id=lambda x: [uuid.uuid4().hex for _ in range(len(x))],
        )[['id', 'text', 'is_human']],
    ),
]

s3_client = S3Client()
S3_MERGED_PATH = s3_client.get_cache_key('merged')
S3_SAMPLE_PATH = s3_client.get_cache_key('merged_sample')

merged_df = None
sample_df = None
if our_namespace.use_s3:
    merged_df = s3_client.download_df(S3_MERGED_PATH)
    sample_df = s3_client.download_df(S3_SAMPLE_PATH)
    print('Successfully downloaded datasets from S3')
else:
    print('Creating datasets locally...')

    datasets_df = [dataset.get_df() for dataset in datasets]
    print(sum(len(dataset) for dataset in datasets_df))
    merged_df = pd.concat(datasets_df, ignore_index=True)
    merged_df = merged_df.drop_duplicates(subset=['text']).reset_index(drop=True)
    print(f'{merged_df.size=}', f'{len(merged_df)=}')

    SAMPLE_SIZE = 100
    sample_df = merged_df.sample(n=SAMPLE_SIZE, random_state=0)

if our_namespace.upload_to_s3:
    s3_client.upload_df(merged_df, S3_MERGED_PATH)
    s3_client.upload_df(sample_df, S3_SAMPLE_PATH)
    print('Successfully created and uploaded datasets to S3')

# Save locally
merged_df.to_csv('merged.csv', index=False)
sample_df.to_csv('merged_sample.csv', index=False)
