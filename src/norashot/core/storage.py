from datetime import datetime
from pathlib import Path

from loguru import logger
from PIL import Image

from norashot.config import SaveConfig


def render_filename(template: str, now: datetime, image_format: str) -> str:
    filename = now.strftime(template)
    suffix = image_format.lower().lstrip(".")

    if not filename.lower().endswith("." + suffix):
        filename = filename + "." + suffix

    return filename


def save_image(image: Image.Image, config: SaveConfig) -> Path:
    folder = Path(config.folder).expanduser()
    folder.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    filename = render_filename(config.filename_template, now, config.image_format)
    target = folder / filename

    image_format = config.image_format.upper()
    if image_format == "JPG":
        image_format = "JPEG"

    logger.info("Saving screenshot | target=%s | format=%s", target, image_format)
    image.save(target, format=image_format)
    logger.info("Screenshot saved | target=%s | size=%sx%s", target, image.width, image.height)

    return target
