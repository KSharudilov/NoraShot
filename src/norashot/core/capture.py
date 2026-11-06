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
    def capture_fullscreen(self, monitor_index: int | None = None) -> Image.Image:
        """Capture the display under the cursor; allow explicit index when needed."""
        with mss.mss() as sct:
            monitors = sct.monitors
            if len(monitors) <= 1:
                raise RuntimeError("No physical displays detected by MSS")

            if monitor_index is None:
                monitor_index = self._monitor_under_cursor(monitors)

            if not 1 <= monitor_index < len(monitors):
                logger.error(
                    "Invalid monitor index | index={} | available={}",
                    monitor_index, len(monitors) - 1,
                )
                raise ValueError(f"Monitor index out of range: {monitor_index}")

            monitor = monitors[monitor_index]
            logger.info(
                "Capturing display | index={} | left={} | top={} | width={} | height={}",
                monitor_index, monitor["left"], monitor["top"],
                monitor["width"], monitor["height"],
            )
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)

        logger.info("Display captured | size={}x{}", image.width, image.height)
        return image

    @staticmethod
    def _monitor_under_cursor(monitors) -> int:
        """Compare Win32 cursor coordinates to MSS physical display rectangles."""
        if sys.platform != "win32":
            logger.warning("Cursor display detection requires Windows; defaulting to primary")
            return 1

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        cursor = POINT()
        if not ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor)):
            logger.warning("GetCursorPos failed; defaulting to primary monitor")
            return 1

        x, y = int(cursor.x), int(cursor.y)
        for index, monitor in enumerate(monitors[1:], start=1):
            left, top = monitor["left"], monitor["top"]
            if left <= x < left + monitor["width"] and top <= y < top + monitor["height"]:
                logger.info(
                    "Display selected from cursor | index={} | cursor_x={} | cursor_y={}",
                    index, x, y,
                )
                return index

        logger.warning(
            "No display contains cursor; using primary | cursor_x={} | cursor_y={}",
            x, y,
        )
        return 1

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
