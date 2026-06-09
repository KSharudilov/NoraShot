from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import mss
from loguru import logger
from PIL import Image


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    width: int
    height: int


class ScreenshotService:
    def capture_fullscreen(self, monitor_index: int = 1) -> Image.Image:
        logger.info("Capturing fullscreen | monitor_index=%s", monitor_index)
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)

        logger.info("Fullscreen captured | size=%sx%s", image.width, image.height)
        return image

    def capture_region(self, region: Region) -> Image.Image:
        logger.info("Capturing region")
        with mss.mss() as sct:
            shot = sct.grab(
                {
                    "left": region.left,
                    "top": region.top,
                    "width": region.width,
                    "height": region.height,
                }
            )
            image = Image.frombytes("RGB", shot.size, shot.rgb)

        logger.info("Region captured | size=%sx%s", image.width, image.height)
        return image

    def capture_active_window(self) -> Optional[Image.Image]:
        logger.warning("Active window capture is not implemented yet")
        return None
