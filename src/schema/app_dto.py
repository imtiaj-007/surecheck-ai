from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse[T](BaseModel):
    """A generic model for paginated API responses."""

    data: list[T]
    current_page: int
    total_pages: int
    total_records: int


class SystemInfo(BaseModel):
    platform: str
    python_version: str
    uptime: str
    uptime_seconds: float


class CPUInfo(BaseModel):
    usage_percent: float
    cores: int
    logical_cores: int


class MemoryInfo(BaseModel):
    total_mb: float
    available_mb: float
    used_mb: float
    usage_percent: float


class DiskInfo(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float


class ResourcesInfo(BaseModel):
    cpu: CPUInfo
    memory: MemoryInfo
    disk: DiskInfo


class ProcessInfo(BaseModel):
    memory_rss_mb: float
    memory_vms_mb: float
    cpu_percent: float
    thread_count: int
    create_time: datetime


class GPUInfo(BaseModel):
    available: bool = False
    gpu_usage_percent: float | None = None
    gpu_memory_used_mb: float | None = None
    gpu_memory_total_mb: float | None = None
    gpu_temperature: float | None = None
    message: str | None = None


class DatabaseDetails(BaseModel):
    status: str
    version: str | None = None
    active_connections: int | None = None
    response_time_ms: str | None = None
    error: str | None = None


class ServicesInfo(BaseModel):
    database: str
    database_details: DatabaseDetails
    redis: str
    aws_s3: str
    api: str


class HealthResponse(BaseModel):
    status: str
    message: str
    version: str
    timestamp: datetime
    system: SystemInfo
    resources: ResourcesInfo
    process: ProcessInfo
    gpu: GPUInfo
    services: ServicesInfo


class LogOptions(BaseModel):
    format: str
    enqueue: bool
    rotation: str
    retention: str
    compression: str
    serialize: bool
    catch: bool
