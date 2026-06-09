from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from norashot.paths import get_config_path, get_default_screenshot_dir


@dataclass
class AppConfig:
    start_minimized: bool = True
    start_with_windows: bool = False
    theme: str = "system"
    language: str = "ru"
    show_notifications: bool = True


@dataclass
class HotkeyConfig:
    area: str = "print_screen"
    fullscreen: str = "ctrl+print_screen"
    active_window: str = "alt+print_screen"
    settings: str = "ctrl+shift+s"


@dataclass
class CaptureConfig:
    open_editor_after_capture: bool = False


@dataclass
class SaveConfig:
    enabled: bool = True
    folder: str = field(default_factory=lambda: str(get_default_screenshot_dir()))
    image_format: str = "png"
    filename_template: str = "screenshot_%Y-%m-%d_%H-%M-%S"


@dataclass
class ClipboardConfig:
    copy_image: bool = True
    copy_file_path: bool = False
    copy_public_url: bool = False


@dataclass
class UploadConfig:
    enabled: bool = False
    provider: str = "s3"
    endpoint: str = "https://s3.ru-1.storage.selcloud.ru"
    bucket: str = ""
    public_base_url: str = ""
    prefix_template: str = "%Y/%m/%d"


@dataclass
class LogsConfig:
    level: str = "INFO"
    retention_days: int = 30


@dataclass
class NoraShotConfig:
    app: AppConfig = field(default_factory=AppConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    save: SaveConfig = field(default_factory=SaveConfig)
    clipboard: ClipboardConfig = field(default_factory=ClipboardConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    logs: LogsConfig = field(default_factory=LogsConfig)


def deep_update_dataclass(instance: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        if not hasattr(instance, key):
            logger.warning("Unknown config key ignored | key=%s", key)
            continue

        current_value = getattr(instance, key)
        if hasattr(current_value, "__dataclass_fields__") and isinstance(value, dict):
            deep_update_dataclass(current_value, value)
        else:
            setattr(instance, key, value)

    return instance


def load_config(path: Path | None = None) -> NoraShotConfig:
    config_path = path or get_config_path()
    config = NoraShotConfig()

    if not config_path.exists():
        logger.info("Config not found, creating default config | path=%s", config_path)
        save_config(config, config_path)
        return config

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or dict()
        if not isinstance(data, dict):
            raise ValueError("Config root must be a dictionary")
        deep_update_dataclass(config, data)
        logger.info("Config loaded | path=%s", config_path)
        return config
    except Exception:
        logger.exception("Failed to load config, using defaults | path=%s", config_path)
        return config


def save_config(config: NoraShotConfig, path: Path | None = None) -> None:
    config_path = path or get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(config)
    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    logger.info("Config saved | path=%s", config_path)
