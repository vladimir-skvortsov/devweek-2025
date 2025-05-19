import os
import boto3
import pandas as pd
from io import BytesIO


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
        return f'{dataset_id.replace("/", "-")}.parquet'

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
