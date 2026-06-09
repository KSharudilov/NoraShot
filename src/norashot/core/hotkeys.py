from __future__ import annotations

import ctypes
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

WM_HOTKEY = 0x0312
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012
WH_KEYBOARD_LL = 13

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_SNAPSHOT = 0x2C
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C

VK_CODES = {
    "print screen": VK_SNAPSHOT,
    "print_screen": VK_SNAPSHOT,
    "prtsc": VK_SNAPSHOT,
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

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_uint),
        ("pt", POINT),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_uint),
        ("scanCode", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p)

user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = ctypes.c_bool
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = ctypes.c_bool
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LowLevelKeyboardProc, ctypes.c_void_p, ctypes.c_uint]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p]
user32.CallNextHookEx.restype = ctypes.c_long
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = ctypes.c_bool
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = ctypes.c_bool
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = ctypes.c_void_p
user32.PostThreadMessageW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
user32.PostThreadMessageW.restype = ctypes.c_bool
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = ctypes.c_uint
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p


@dataclass
class HotkeyBinding:
    hotkey_id: int
    source: str
    normalized: str
    modifiers: int
    vk_code: int
    callback: Callable[[], None]
    register_ok: bool = False


class HotkeyManager(QAbstractNativeEventFilter):
    def __init__(self) -> None:
        super().__init__()
        self._bindings: dict[int, HotkeyBinding] = dict()
        self._next_id = 100
        self._started = False
        self._hook_handle = None
        self._hook_thread: threading.Thread | None = None
        self._hook_thread_id = 0
        self._hook_callback = None

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
            ctypes.set_last_error(0)
            result = user32.RegisterHotKey(None, binding.hotkey_id, flags, binding.vk_code)
            if result:
                binding.register_ok = True
                logger.info("Hotkey registered successfully | id=" + str(binding.hotkey_id) + " | hotkey=" + binding.normalized)
            else:
                error_code = ctypes.get_last_error()
                logger.error("Failed to register hotkey | id=" + str(binding.hotkey_id) + " | hotkey=" + binding.normalized + " | error=" + str(error_code))

        self._start_keyboard_hook()
        self._started = True
        logger.info("Native Windows hotkey manager started")

    def stop(self) -> None:
        logger.info("Stopping native Windows hotkey manager")
        self._stop_keyboard_hook()

        if sys.platform == "win32":
            for binding in self._bindings.values():
                if not binding.register_ok:
                    continue
                try:
                    user32.UnregisterHotKey(None, binding.hotkey_id)
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

        logger.info("Hotkey triggered by RegisterHotKey | id=" + str(hotkey_id) + " | hotkey=" + binding.normalized)
        self._call_binding(binding)
        return True, 0

    def _start_keyboard_hook(self) -> None:
        if self._hook_thread is not None:
            return
        logger.info("Starting low level keyboard hook for PrintScreen combinations")
        self._hook_thread = threading.Thread(target=self._keyboard_hook_loop, daemon=True)
        self._hook_thread.start()

    def _stop_keyboard_hook(self) -> None:
        if self._hook_thread_id:
            try:
                user32.PostThreadMessageW(self._hook_thread_id, WM_QUIT, 0, 0)
            except Exception:
                logger.exception("Failed to stop keyboard hook thread")
        self._hook_thread = None
        self._hook_thread_id = 0

    def _keyboard_hook_loop(self) -> None:
        self._hook_thread_id = kernel32.GetCurrentThreadId()
        self._hook_callback = LowLevelKeyboardProc(self._low_level_keyboard_proc)
        module_handle = kernel32.GetModuleHandleW(None)

        ctypes.set_last_error(0)
        self._hook_handle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_callback, module_handle, 0)
        if not self._hook_handle:
            error_code = ctypes.get_last_error()
            logger.error("Failed to install low level keyboard hook | error=" + str(error_code))
            return

        logger.info("Low level keyboard hook installed | thread_id=" + str(self._hook_thread_id))
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        try:
            user32.UnhookWindowsHookEx(self._hook_handle)
            logger.info("Low level keyboard hook removed")
        except Exception:
            logger.exception("Failed to remove low level keyboard hook")
        self._hook_handle = None

    def _low_level_keyboard_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code >= 0 and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
            event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if event.vkCode == VK_SNAPSHOT:
                self._handle_print_screen_hook_event()
        return user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

    def _handle_print_screen_hook_event(self) -> None:
        modifiers = self._current_modifiers()
        logger.info("PrintScreen hook event | modifiers=" + str(modifiers))

        for binding in self._bindings.values():
            if binding.vk_code != VK_SNAPSHOT:
                continue
            if binding.modifiers != modifiers:
                continue
            if binding.register_ok:
                logger.info("PrintScreen hook ignored because RegisterHotKey owns this hotkey | hotkey=" + binding.normalized)
                return
            logger.info("Hotkey triggered by keyboard hook | id=" + str(binding.hotkey_id) + " | hotkey=" + binding.normalized)
            self._call_binding(binding)
            return

    def _current_modifiers(self) -> int:
        modifiers = 0
        if user32.GetAsyncKeyState(VK_MENU) & 0x8000:
            modifiers |= MOD_ALT
        if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
            modifiers |= MOD_CONTROL
        if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
            modifiers |= MOD_SHIFT
        if user32.GetAsyncKeyState(VK_LWIN) & 0x8000:
            modifiers |= MOD_WIN
        if user32.GetAsyncKeyState(VK_RWIN) & 0x8000:
            modifiers |= MOD_WIN
        return modifiers

    def _call_binding(self, binding: HotkeyBinding) -> None:
        try:
            binding.callback()
        except Exception:
            logger.exception("Hotkey callback failed | hotkey=" + binding.normalized)

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
