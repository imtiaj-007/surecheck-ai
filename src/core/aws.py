from src.core.config import settings


class AWSConfig:
    """
    Configuration class for AWS settings.

    This class holds AWS configuration parameters required for establishing
    connections to S3, Lambda, etc.

    Attributes:
        aws_access_key (str): AWS access key ID for authentication
        aws_secret_key (str): AWS secret access key for authentication
        region (str): AWS region name (defaults to 'ap-south-1' if not specified)
        bucket_name (str): Name of the S3 bucket to interact with
    """

    aws_access_key = settings.AWS_ACCESS_KEY
    aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    region = settings.AWS_REGION or "ap-south-1"
    bucket_name = settings.AWS_BUCKET_NAME

    if not all([aws_access_key, aws_secret_key, bucket_name]):
        raise ValueError("Missing required AWS credentials or bucket configuration")
