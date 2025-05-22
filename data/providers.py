import os
import kagglehub
import pandas as pd
import utils
import glob
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable
from charset_normalizer import from_bytes
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from S3Client import S3Client

load_dotenv()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=500,
    length_function=len,
    is_separator_regex=False,
    separators=['\n\n', '\n', '.', '!', '?', ',', ' ', '\uff0e', '\u3002'],
)


class Provider(ABC):
    def __init__(self, dataset_id: str, transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        self.dataset_id = dataset_id
        self.transform_func = transform_func
        self.s3 = S3Client()

    def _filter(self, df: pd.DataFrame) -> pd.DataFrame:
        df['text_clean'] = df['text'].astype(str).apply(utils.clean)
        df = df.drop_duplicates(subset=['text_clean']).reset_index(drop=True)
        df['text'] = df['text_clean']
        df = df.drop(columns=['text_clean'])

        # Process texts and create new rows for split texts
        new_rows = []
        for _, row in df.iterrows():
            text = row['text']
            if len(text) >= 2000:  # Only split texts longer than 2000 characters
                chunks = text_splitter.split_text(text)
                for chunk in chunks:
                    if len(chunk) >= 80:  # Keep only chunks that meet minimum length
                        new_row = row.copy()
                        new_row['text'] = chunk
                        new_rows.append(new_row)
            elif len(text) >= 80:  # Keep original texts that meet minimum length
                new_rows.append(row)

        # Create new dataframe with split texts
        return pd.DataFrame(new_rows).reset_index(drop=True)

    def get_df(self) -> pd.DataFrame:
        cache_key: str = self.s3.get_cache_key(self.dataset_id)

        if self.s3.exists(cache_key):
            print(f'Loading {self.dataset_id} from cache')
            return self.s3.download_df(cache_key)

        print(f'Downloading and transforming {self.dataset_id}')
        df = self._download()
        df = self.transform_func(df)

        df = self._filter(df)

        if '__index_level_0__' in df.columns:
            df = df.drop(columns=['__index_level_0__'])

        print(f'Caching {self.dataset_id} {cache_key}')
        self.s3.upload_df(df, cache_key)

        return df

    @abstractmethod
    def _download(self) -> pd.DataFrame:
        pass


class KaggleProvider(Provider):
    def __init__(self, dataset_id: str, files: list[str], transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        super().__init__(f'kaggle_{dataset_id}', transform_func)
        self.dataset_id = dataset_id
        self.files = files

    def _download(self) -> pd.DataFrame:
        path = kagglehub.dataset_download(self.dataset_id)
        available_files = os.listdir(path)
        csv_files = [f for f in available_files if f.endswith('.csv')]

        # Find intersection of requested files and available CSV files
        matching_files = [f for f in self.files if f in csv_files]
        if not matching_files:
            raise Exception(
                f'None of the requested files {self.files} found in {self.dataset_id}. Available files: {csv_files}'
            )

        # Read and concatenate all matching files
        dfs = [pd.read_csv(os.path.join(path, f)) for f in matching_files]
        return pd.concat(dfs, ignore_index=True)


class KaggleCompetitionProvider(Provider):
    def __init__(
        self,
        competition_slug: str,
        csv_filename: str,
        transform_func: Callable[[pd.DataFrame], pd.DataFrame],
    ):
        stem = Path(csv_filename).stem
        cache_key = f'kaggle_comp_{competition_slug}_{stem}'
        super().__init__(cache_key, transform_func)
        self.competition_slug = competition_slug
        self.csv_filename = csv_filename

    def _download(self) -> pd.DataFrame:
        csv_path = kagglehub.competition_download(
            self.competition_slug,
            path=self.csv_filename,
            force_download=False,
        )
        return pd.read_csv(csv_path)


class KaggleTxtProvider(Provider):
    def __init__(self, dataset_id: str, transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        super().__init__(f'kaggle_txt_{dataset_id}', transform_func)
        self.dataset_id = dataset_id

    def _download(self) -> pd.DataFrame:
        path = kagglehub.dataset_download(self.dataset_id)
        txt_files = glob.glob(os.path.join(path, '**', '*.txt'), recursive=True)
        if not txt_files:
            raise RuntimeError(f'No .txt files found in {self.dataset_id}')
        rows = []
        for fp in txt_files:
            raw = Path(fp).read_bytes()
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = from_bytes(raw).best().output()  # there are strange symbols (Old Russian, etc.), observe this
            rows.append({'text': text})
        return pd.DataFrame(rows)


class HuggingFaceProvider(Provider):
    def __init__(self, dataset_id: str, transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        super().__init__(f'hf_{dataset_id}', transform_func)
        self.dataset_id = dataset_id

    def _download(self) -> pd.DataFrame:
        from datasets import load_dataset

        ds = load_dataset(self.dataset_id, split='train')
        return ds.to_pandas()


class FileProvider(Provider):
    def __init__(self, file_path: str, transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        super().__init__(f'file_{Path(file_path).stem}', transform_func)
        self.file_path = file_path

    def _download(self) -> pd.DataFrame:
        return pd.read_csv(self.file_path)
