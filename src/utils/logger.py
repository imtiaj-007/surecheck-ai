import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.core.config import settings
from src.schema.app_dto import LogOptions


class LogConfig:
    """Centralized logging configuration"""

    def __init__(self) -> None:
        self.base_dir = Path(settings.BASE_DIR) / "logs"
        self._configure_logger()

    def _get_log_file_path(self, log_type: str) -> str:
        """Generate log file path with current date"""
        log_dir = self.base_dir / f"{log_type}_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir / f"{log_type}_log_{datetime.now():%Y-%m-%d}.log")

    def _configure_logger(self) -> None:
        """Configure all logger instances"""
        logger.remove()

        common_config = LogOptions(
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | Module: {module:<8} | Fn: {function:<12} | Line: {line} - {message}",
            enqueue=True,
            rotation=settings.LOG_ROTATION or "00:00",
            retention=settings.LOG_RETENTION or "7 days",
            compression="zip",
            serialize=True,
            catch=True,
        )

        # Configure log handlers with proper file and line formatting
        logger.add(
            sink=self._get_log_file_path("app"),
            level="INFO",
            filter=lambda r: r["level"].name == "INFO",
            **common_config.model_dump(),
        )

        logger.add(
            self._get_log_file_path("error"),
            level="ERROR",
            filter=lambda r: r["level"].name == "ERROR",
            **common_config.model_dump(),
        )

        logger.add(
            self._get_log_file_path("db_error"),
            level="CRITICAL",
            filter=lambda r: r["extra"].get("database") or False,
            **common_config.model_dump(),
        )

        logger.add(
            self._get_log_file_path("audit"),
            level="INFO",
            filter=lambda r: r["extra"].get("audit") or False,
            **common_config.model_dump(),
        )

        logger.add(
            self._get_log_file_path("performance"),
            level="DEBUG",
            filter=lambda r: r["extra"].get("performance") or False,
            **common_config.model_dump(),
        )

        # Add console handler for development with file and line info
        if settings.APP_ENV in ["development", "staging"]:
            logger.add(
                sys.stdout,
                level="DEBUG",
                colorize=True,
                backtrace=True,
                diagnose=True,
                format="<level>{level}: \t</level> <yellow>{time:YYYY-MM-DD HH:mm:ss}</yellow> | <cyan>Module: {module:<8}</cyan> | <cyan>Fn: {function:<12}</cyan> | <cyan>Line: {line}</cyan> - \n<level>{message}</level>",
            )

    # Add proxy methods to make LogConfig behave like a logger instance
    def info(self, message: str) -> None:
        """Log an info message"""
        logger.opt(depth=1).info(message)

    def error(self, message: str) -> None:
        """Log an error message"""
        logger.opt(depth=1).error(message)

    def warning(self, message: str) -> None:
        """Log a warning message"""
        logger.opt(depth=1).warning(message)

    def debug(self, message: str) -> None:
        """Log a debug message"""
        logger.opt(depth=1).debug(message)

    def critical(self, message: str) -> None:
        """Log a critical message"""
        logger.opt(depth=1).critical(message)

    def exception(self, message: str) -> None:
        """Log an exception with traceback"""
        logger.opt(depth=1).exception(message)


# Singletone Log Instance
log: LogConfig = LogConfig()
