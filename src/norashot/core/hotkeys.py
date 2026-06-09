from __future__ import annotations

from collections.abc import Callable

from loguru import logger


class HotkeyManager:
    def __init__(self) -> None:
        self._registered: dict[str, Callable[[], None]] = dict()

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        logger.info("Registering hotkey placeholder | hotkey=%s", hotkey)
        self._registered[hotkey] = callback

    def start(self) -> None:
        logger.info("Hotkey manager placeholder started")
        logger.warning("Global hotkeys are not implemented in this skeleton yet")

    def stop(self) -> None:
        logger.info("Hotkey manager stopped")
        self._registered.clear()
