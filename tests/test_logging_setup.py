"""Regression: GUI/windowed executables do not have sys.stderr."""
from __future__ import annotations

import sys

from loguru import logger
from norashot import logging_setup


def test_file_logging_without_console(monkeypatch, tmp_path):
    monkeypatch.setattr(logging_setup, "get_log_dir", lambda: tmp_path)
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "stdout", None)
    try:
        logfile = logging_setup.setup_logging(level="DEBUG", retention_days=7)
        logger.info("GUI startup without console works")
        logger.complete()
        assert logfile.exists()
        assert "GUI startup without console works" in logfile.read_text(encoding="utf-8")
    finally:
        logger.remove()


def test_file_logging_with_console(monkeypatch, tmp_path):
    monkeypatch.setattr(logging_setup, "get_log_dir", lambda: tmp_path)
    try:
        logfile = logging_setup.setup_logging(level="INFO")
        logger.info("Console startup works")
        logger.complete()
        assert "Console startup works" in logfile.read_text(encoding="utf-8")
    finally:
        logger.remove()
