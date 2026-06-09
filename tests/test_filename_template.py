from datetime import datetime

from norashot.core.storage import render_filename


def test_render_filename_adds_extension():
    now = datetime(2026, 6, 5, 15, 30, 12)
    result = render_filename("screenshot_%Y-%m-%d_%H-%M-%S", now, "png")
    assert result == "screenshot_2026-06-05_15-30-12.png"


def test_render_filename_keeps_existing_extension():
    now = datetime(2026, 6, 5, 15, 30, 12)
    result = render_filename("screen.png", now, "png")
    assert result == "screen.png"
