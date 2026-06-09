from __future__ import annotations

import threading
from collections.abc import Callable

import keyboard
from loguru import logger


class HotkeyManager:
    def __init__(self) -> None:
        self._registered: dict[str, Callable[[], None]] = dict()
        self._started = False

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        normalized = self._normalize_hotkey(hotkey)
        logger.info("Registering hotkey | source=" + hotkey + " | normalized=" + normalized)
        self._registered[normalized] = callback

    def start(self) -> None:
        if self._started:
            logger.warning("Hotkey manager is already started")
            return

        logger.info("Starting hotkey manager")
        for hotkey, callback in self._registered.items():
            try:
                keyboard.add_hotkey(
                    hotkey,
                    self._wrap_callback(hotkey, callback),
                    suppress=False,
                    trigger_on_release=True,
                )
                logger.info("Hotkey registered successfully | hotkey=" + hotkey)
            except Exception:
                logger.exception("Failed to register hotkey | hotkey=" + hotkey)

        self._started = True
        logger.info("Hotkey manager started")

    def stop(self) -> None:
        logger.info("Stopping hotkey manager")
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            logger.exception("Failed to unhook hotkeys")

        self._registered.clear()
        self._started = False
        logger.info("Hotkey manager stopped")

    def _wrap_callback(self, hotkey: str, callback: Callable[[], None]) -> Callable[[], None]:
        def runner() -> None:
            logger.info("Hotkey triggered | hotkey=" + hotkey)
            thread = threading.Thread(
                target=self._safe_call,
                args=(hotkey, callback),
                daemon=True,
            )
            thread.start()

        return runner

    def _safe_call(self, hotkey: str, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:
            logger.exception("Hotkey callback failed | hotkey=" + hotkey)

    def _normalize_hotkey(self, hotkey: str) -> str:
        value = hotkey.strip().lower()
        value = value.replace("print_screen", "print screen")
        value = value.replace("prtsc", "print screen")
        value = value.replace("ctrl", "ctrl")
        value = value.replace("control", "ctrl")
        return value
