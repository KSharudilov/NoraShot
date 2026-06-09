from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir

APP_NAME = "NoraShot"
APP_AUTHOR = "NoraShot"


def get_config_dir() -> Path:
    path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir() -> Path:
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    path = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_screenshot_dir() -> Path:
    path = Path.home() / "Pictures" / "NoraShot"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_config_dir() / "config.yaml"
