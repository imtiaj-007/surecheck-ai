from pydantic import BaseModel


class PresignedUrlResponse(BaseModel):
    url: str
    file_key: str
    expires_in: int
    mime_type: str | None = None


class FileMetadata(BaseModel):
    """Internal helper for validation results"""

    extension: str
    mime_type: str
    size: int | None = None
