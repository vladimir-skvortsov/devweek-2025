import os
from io import BytesIO
from abc import ABC, abstractmethod
from typing import Callable
import boto3
import pandas as pd
import kagglehub
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


class S3Client:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=os.getenv('S3_ENDPOINT_URL'),
            aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
            region_name='ru-central1',
        )
        self.bucket = os.getenv('S3_BUCKET')

    def get_cache_key(self, dataset_id: str) -> str:
        return f'{dataset_id}.parquet'

    def exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False

    def upload_df(self, df: pd.DataFrame, key: str):
        buffer = BytesIO()
        df.to_parquet(buffer)
        buffer.seek(0)
        self.s3.upload_fileobj(buffer, self.bucket, key)

    def download_df(self, key: str) -> pd.DataFrame:
        buffer = BytesIO()
        self.s3.download_fileobj(self.bucket, key, buffer)
        buffer.seek(0)
        return pd.read_parquet(buffer)


class Provider(ABC):
    def __init__(self, dataset_id: str, transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        self.dataset_id = dataset_id
        self.transform_func = transform_func
        self.s3 = S3Client()

    def get_df(self) -> pd.DataFrame:
        cache_key: str = self.s3.get_cache_key(self.dataset_id)

        if self.s3.exists(cache_key):
            print(f'Loading {self.dataset_id} from cache')
            return self.s3.download_df(cache_key)

        print(f'Downloading and transforming {self.dataset_id}')
        df = self._download()
        df = self.transform_func(df)

        print(f'Caching {self.dataset_id} {cache_key}')
        self.s3.upload_df(df, cache_key)

        return df

    @abstractmethod
    def _download(self) -> pd.DataFrame:
        pass


class KaggleProvider(Provider):
    def __init__(self, dataset_id: str, transform_func: Callable[[pd.DataFrame], pd.DataFrame]):
        super().__init__(f'kaggle_{dataset_id}', transform_func)
        self.dataset_id = dataset_id

    def _download(self) -> pd.DataFrame:
        path = kagglehub.dataset_download(self.dataset_id)
        files = os.listdir(path)
        csv_files = [f for f in files if f.endswith('.csv')]
        if not csv_files:
            raise Exception(f'No CSV files found in {self.dataset_id}')
        return pd.read_csv(os.path.join(path, csv_files[0]))


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
