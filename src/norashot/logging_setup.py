import sys
from pathlib import Path

from loguru import logger

from norashot.paths import get_log_dir


def setup_logging(level: str = "INFO", retention_days: int = 30) -> Path:
    log_dir = get_log_dir()
    log_file = log_dir / "norashot.log"

    logger.remove()
    # PyInstaller --windowed (runw.exe) has no console: sys.stderr is None.
    # File logging must work regardless of whether a terminal is attached.
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
            diagnose=False,
        )
    logger.add(
        log_file,
        level=level,
        rotation="10 MB",
        retention=f"{max(1, int(retention_days))} days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,  # Never expose locals such as credentials on exception traces.
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
    )

    logger.info("Logging initialized | level={} | retention_days={} | file={}", level, retention_days, log_file)
    return log_file
