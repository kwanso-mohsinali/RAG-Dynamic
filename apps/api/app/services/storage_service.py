import logging
import boto3
import os
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for handling S3 Storage operations.
    """

    def __init__(self):
        """Initialize the storage service with S3 client."""

        self.bucket_name = settings.AWS_BUCKET_NAME
        if not self.bucket_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AWS_BUCKET_NAME environment variable is required",
            )

        try:
            self.s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to access bucket '{self.bucket_name}'. Please check your credentials and bucket name. Error: {str(e)}",
            )

    def file_exists(self, file_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            file_key: Path to the file in the bucket

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            logger.error(f"Error checking file existence for {file_key}: {str(e)}")
            return False

    def download_file(self, file_key: str, local_path: str):
        """
        Download a file from S3 to local filesystem.

        Args:
            file_key: Path to the file in the bucket
            local_path: Local path where to save the file

        Returns:
            str: Local file path where file was saved

        Raises:
            HTTPException: If download fails
        """
        try:
            # Check if file exists in S3
            if not self.file_exists(file_key):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found in S3: {file_key}",
                )

            # Create directory if it doesn't exist
            dir_name = os.path.dirname(local_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            # Download the file
            self.s3.download_file(self.bucket_name, file_key, local_path)
            return local_path
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file from S3: {str(e)}",
            )
