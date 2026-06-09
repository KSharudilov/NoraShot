import sys
from pathlib import Path

from loguru import logger

from norashot.paths import get_log_dir


def setup_logging(level: str = "INFO") -> Path:
    log_dir = get_log_dir()
    log_file = log_dir / "norashot.log"

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
    )
    logger.add(
        log_file,
        level=level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
    )

    logger.info("Logging initialized | level={} | file={}", level, log_file)
    return log_file
