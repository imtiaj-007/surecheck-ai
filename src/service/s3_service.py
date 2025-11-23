import io
import re
from datetime import datetime
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from mypy_boto3_s3.client import S3Client

from src.core.aws import AWSConfig
from src.schema.file_dto import FileMetadata, PresignedUrlResponse
from src.utils.logger import log


class S3Manager:
    """
    Manager class for handling Amazon S3 operations with error handling, validation, and caching.

    This class provides high-level functionality for uploading, downloading, and generating presigned
    URLs for files, as well as file validation and key generation.

    Attributes:
        config (AWSConfig): Holds AWS credentials and settings
        _client (S3Client | None): Cached S3 client, lazily instantiated
        UPLOAD_FOLDER (str): Base path for uploaded files in the S3 bucket
        SAFE_FILENAME_REGEX (re.Pattern): Regex pattern for validating safe filenames
        MAX_FILE_SIZE (int): Maximum allowed upload file size in bytes
        ALLOWED_EXTENSIONS (set[str]): Allowed file extensions
        MIME_TYPES (dict[str, str]): Mapping of file extensions to MIME types
    """

    def __init__(self) -> None:
        """
        Initialize the S3Manager instance.

        This sets up configuration using application AWS settings, prepares the S3 client cache,
        and defines upload folder, validation patterns, file extension whitelist, and MIME type mapping.
        """
        self.config = AWSConfig()
        self._client: S3Client | None = None

        self.UPLOAD_FOLDER = "surecheck/uploads"
        self.SAFE_FILENAME_REGEX = re.compile(r"^[\w\-. ]+$")
        self.MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

        self.ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
        self.MIME_TYPES = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }

    @property
    def client(self) -> S3Client:
        """
        Get a cached boto3 S3 client, lazily instantiating it if necessary.

        Returns:
            S3Client: The S3 client configured with AWS credentials/region

        Raises:
            HTTPException: If the S3 client cannot be created for any reason.
        """
        if self._client is None:
            try:
                self._client = boto3.client(
                    "s3",
                    region_name=self.config.region,
                    aws_access_key_id=self.config.aws_access_key,
                    aws_secret_access_key=self.config.aws_secret_key,
                    config=Config(signature_version="s3v4"),
                )
            except Exception as e:
                log.error(f"Failed to initialize S3 client: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 Connection Error"
                ) from e
        return self._client

    def _validate_file_params(self, filename: str, file_size: int | None = None) -> FileMetadata:
        """
        Validate file upload parameters.

        This method checks filename presence, structure, allowed extensions, MIME type,
        and (optionally) the file size.

        Args:
            filename (str): Name of the file to validate.
            file_size (Optional[int]): File size in bytes; if provided, it is checked.

        Returns:
            FileMetadata: Information about extension, MIME type, and size.

        Raises:
            ValueError: For empty, unsafe or unsupported file type/extension/type.
            HTTPException: For files that exceed the allowed size.
        """
        try:
            if not filename:
                raise ValueError("Filename must not be empty")

            if not self.SAFE_FILENAME_REGEX.match(filename):
                raise ValueError("Invalid filename format")

            file_path = Path(filename)
            ext = file_path.suffix.lower()

            if ext not in self.ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported file extension for {ext}. Allowed: {self.ALLOWED_EXTENSIONS}"
                )

            mime_type = self.MIME_TYPES.get(ext)
            if mime_type is None:
                raise ValueError(f"Unsupported mime type for {ext}")

            if file_size and file_size > self.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File size should be within {self.MAX_FILE_SIZE / 1048576}MB",
                )
            return FileMetadata(extension=ext, mime_type=mime_type, size=file_size)

        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Error validating file parameters: {e}")
            raise ValueError(f"File validation failed: {e}") from e

    def _build_file_key(self, filename: str) -> str:
        """
        Build a unique S3 file key with a timestamp, preserving extension.

        Args:
            filename (str): Original filename.

        Returns:
            str: S3 key including upload folder and timestamp.

        Raises:
            ValueError: If the key cannot be constructed.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = Path(filename)
            base = file_path.stem
            ext = file_path.suffix
            unique_filename = f"{base}_{timestamp}{ext}"
            return f"{self.UPLOAD_FOLDER}/{unique_filename}"
        except Exception as e:
            log.error(f"Error building file key for {filename}: {e}")
            raise ValueError(f"Failed to generate file key: {e}") from e

    def upload_file_sync(self, file_bytes: bytes, file_name: str) -> str:
        """
        Upload a file to S3 synchronously.

        Used for background file uploads in FastAPI (e.g., BackgroundTasks).

        Args:
            file_bytes (bytes): Content of the file to upload.
            file_name (str): Name of the file (original or generated).

        Returns:
            str: The resulting S3 file key for the uploaded file.

        Raises:
            HTTPException: If the upload fails due to S3/client error.
        """
        try:
            file_key = self._build_file_key(file_name)
            self.client.upload_fileobj(
                Fileobj=io.BytesIO(file_bytes), Bucket=self.config.bucket_name, Key=file_key
            )
            log.info(f"✅ Background Upload Successful: {file_key}")
            return file_key

        except ClientError as e:
            log.error(f"❌ S3 Upload Failed: {e}")
            raise HTTPException(status_code=500, detail="S3 Upload Failed") from e

    def download_file(self, file_key: str) -> bytes:
        """
        Download a file from S3 and return its content as bytes.

        Args:
            file_key (str): The key (path) to the file in S3.

        Returns:
            bytes: The content of the file.

        Raises:
            HTTPException: With 404 if file is not found, or 500 for AWS/permission/internal errors.
        """
        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=file_key)
            body: bytes = response["Body"].read()
            return body

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                log.error(f"File not found in S3: {file_key}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_key}"
                ) from e
            elif error_code in ["AccessDenied", "Forbidden"]:
                log.error(f"AWS access denied for file: {file_key}, error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Access denied to S3 resource",
                ) from e
            else:
                log.error(f"AWS S3 error downloading file {file_key}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error downloading from S3",
                ) from e

        except Exception as e:
            log.error(f"Unexpected error downloading file {file_key}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during file download",
            ) from e

    def get_upload_url(
        self,
        filename: str,
        file_size: int,
        expiration: int = 3600,
    ) -> PresignedUrlResponse:
        """
        Generate a presigned URL for uploading a file directly to S3.

        Validates file parameters (name, extension, size), generates a new S3 key,
        and creates a presigned 'put_object' URL for direct upload.

        Args:
            filename (str): Name of the file to upload.
            file_size (int): Size of the file to upload.
            expiration (int): Validity of the presigned URL in seconds (default: 3600).

        Returns:
            PresignedUrlResponse: URL and metadata needed for upload.

        Raises:
            HTTPException: If generating the presigned URL fails.
        """
        try:
            file_info = self._validate_file_params(filename=filename, file_size=file_size)
            file_key = self._build_file_key(filename)

            url = self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.config.bucket_name,
                    "Key": file_key,
                    "ContentType": file_info.mime_type,
                },
                ExpiresIn=expiration,
            )

            return PresignedUrlResponse(
                url=url,
                file_key=file_key,
                expires_in=expiration,
                mime_type=file_info.mime_type,
            )

        except ClientError as e:
            log.error(f"AWS S3 error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating presigned URL",
            ) from e

        except Exception as e:
            log.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e

    def get_download_url(self, file_key: str, expiration: int = 3600) -> PresignedUrlResponse:
        """
        Generate a presigned URL for downloading a file from S3 (GET object).

        The method verifies if the file exists, and then produces a presigned URL for downloads.

        Args:
            file_key (str): The S3 file key for the object.
            expiration (int): Validity (in seconds) for the presigned URL.

        Returns:
            PresignedUrlResponse: Information including URL and file key for downloading.

        Raises:
            HTTPException: 404 if file is not found, or 500 for other errors.
        """
        try:
            self.client.head_object(Bucket=self.config.bucket_name, Key=file_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
                ) from e
            raise

        url = self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.config.bucket_name, "Key": file_key},
            ExpiresIn=expiration,
        )

        return PresignedUrlResponse(url=url, file_key=file_key, expires_in=expiration)


# Singleton instance for application-wide import
s3_service: S3Manager = S3Manager()
