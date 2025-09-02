import boto3
import os

def download_file_from_s3(file_key: str, bucket_name: str = None):
    bucket_name = bucket_name or os.getenv("AWS_S3_BUCKET_NAME")
    local_path = f"/tmp/{file_key}"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    s3.download_file(bucket_name, file_key, local_path)
    return local_path
