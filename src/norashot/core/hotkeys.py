from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_CODES = {
    "print screen": 0x2C,
    "print_screen": 0x2C,
    "prtsc": 0x2C,
    "s": 0x53,
}

MODIFIER_ALIASES = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
}


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_uint),
        ("pt", POINT),
    ]


@dataclass
class HotkeyBinding:
    hotkey_id: int
    source: str
    normalized: str
    modifiers: int
    vk_code: int
    callback: Callable[[], None]


class HotkeyManager(QAbstractNativeEventFilter):
    def __init__(self) -> None:
        super().__init__()
        self._bindings: dict[int, HotkeyBinding] = dict()
        self._next_id = 100
        self._started = False

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        normalized = self._normalize_hotkey(hotkey)
        modifiers, vk_code = self._parse_hotkey(normalized)
        hotkey_id = self._next_id
        self._next_id += 1
        self._bindings[hotkey_id] = HotkeyBinding(
            hotkey_id=hotkey_id,
            source=hotkey,
            normalized=normalized,
            modifiers=modifiers,
            vk_code=vk_code,
            callback=callback,
        )
        logger.info("Hotkey queued | id=" + str(hotkey_id) + " | source=" + hotkey + " | normalized=" + normalized)

    def start(self) -> None:
        if sys.platform != "win32":
            logger.warning("Native hotkeys are currently supported only on Windows")
            return

        if self._started:
            logger.warning("Hotkey manager is already started")
            return

        app = QCoreApplication.instance()
        if app is None:
            logger.error("Cannot start hotkeys because QCoreApplication is not initialized")
            return

        app.installNativeEventFilter(self)
        logger.info("Starting native Windows hotkey manager")

        for binding in self._bindings.values():
            flags = binding.modifiers | MOD_NOREPEAT
            result = ctypes.windll.user32.RegisterHotKey(
                None,
                binding.hotkey_id,
                flags,
                binding.vk_code,
            )
            if result:
                logger.info("Hotkey registered successfully | id=" + str(binding.hotkey_id) + " | hotkey=" + binding.normalized)
            else:
                error_code = ctypes.get_last_error()
                logger.error("Failed to register hotkey | id=" + str(binding.hotkey_id) + " | hotkey=" + binding.normalized + " | error=" + str(error_code))

        self._started = True
        logger.info("Native Windows hotkey manager started")

    def stop(self) -> None:
        logger.info("Stopping native Windows hotkey manager")
        if sys.platform == "win32":
            for binding in self._bindings.values():
                try:
                    ctypes.windll.user32.UnregisterHotKey(None, binding.hotkey_id)
                    logger.info("Hotkey unregistered | id=" + str(binding.hotkey_id) + " | hotkey=" + binding.normalized)
                except Exception:
                    logger.exception("Failed to unregister hotkey | id=" + str(binding.hotkey_id))

        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.removeNativeEventFilter(self)
            except Exception:
                logger.exception("Failed to remove native event filter")

        self._started = False
        logger.info("Native Windows hotkey manager stopped")

    def nativeEventFilter(self, event_type: bytes | bytearray | str, message: Any) -> tuple[bool, int]:
        try:
            msg = MSG.from_address(int(message))
        except Exception:
            return False, 0

        if msg.message != WM_HOTKEY:
            return False, 0

        hotkey_id = int(msg.wParam)
        binding = self._bindings.get(hotkey_id)
        if binding is None:
            logger.warning("Unknown WM_HOTKEY received | id=" + str(hotkey_id))
            return False, 0

        logger.info("Hotkey triggered | id=" + str(hotkey_id) + " | hotkey=" + binding.normalized)
        try:
            binding.callback()
        except Exception:
            logger.exception("Hotkey callback failed | hotkey=" + binding.normalized)

        return True, 0

    def _normalize_hotkey(self, hotkey: str) -> str:
        value = hotkey.strip().lower()
        value = value.replace("print_screen", "print screen")
        value = value.replace("prtsc", "print screen")
        value = value.replace("control", "ctrl")
        value = value.replace(" ", "")
        value = value.replace("printscreen", "print screen")
        return value

    def _parse_hotkey(self, hotkey: str) -> tuple[int, int]:
        parts = [part.strip() for part in hotkey.split("+") if part.strip()]
        if not parts:
            raise ValueError("Hotkey is empty")

        modifiers = 0
        key_parts: list[str] = list()
        for part in parts:
            modifier = MODIFIER_ALIASES.get(part)
            if modifier is not None:
                modifiers |= modifier
            else:
                key_parts.append(part)

        key_name = "+".join(key_parts)
        vk_code = VK_CODES.get(key_name)
        if vk_code is None and len(key_name) == 1:
            vk_code = ord(key_name.upper())

        if vk_code is None:
            raise ValueError("Unsupported hotkey key: " + key_name)

        return modifiers, vk_code
