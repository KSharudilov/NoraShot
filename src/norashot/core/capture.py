from __future__ import annotations

import ctypes
import sys
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


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class ScreenshotService:
    def capture_fullscreen(self, monitor_index: int = 1) -> Image.Image:
        logger.info("Capturing fullscreen | monitor_index=" + str(monitor_index))
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)

        logger.info("Fullscreen captured | size=" + str(image.width) + "x" + str(image.height))
        return image

    def capture_region(self, region: Region) -> Image.Image:
        logger.info(
            "Capturing region | left=" + str(region.left)
            + " | top=" + str(region.top)
            + " | width=" + str(region.width)
            + " | height=" + str(region.height)
        )
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

        logger.info("Region captured | size=" + str(image.width) + "x" + str(image.height))
        return image

    def capture_active_window(self) -> Optional[Image.Image]:
        if sys.platform != "win32":
            logger.warning("Active window capture is currently supported only on Windows")
            return None

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            logger.warning("Cannot capture active window because foreground window was not found")
            return None

        rect = RECT()
        ok = ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if not ok:
            logger.warning("Cannot capture active window because GetWindowRect failed")
            return None

        left = int(rect.left)
        top = int(rect.top)
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)

        if width <= 0 or height <= 0:
            logger.warning("Cannot capture active window because window size is invalid")
            return None

        logger.info(
            "Active window detected | hwnd=" + str(hwnd)
            + " | left=" + str(left)
            + " | top=" + str(top)
            + " | width=" + str(width)
            + " | height=" + str(height)
        )
        return self.capture_region(Region(left=left, top=top, width=width, height=height))
