"""
desktop_use - Desktop automation toolkit for Windows.

Provides a FastAPI HTTP/WebSocket server for controlling the mouse, keyboard,
windows, clipboard, and performing OCR / template matching on Windows desktops.
"""

__version__ = "0.1.0"

from desktop_use.client import DesktopAgent

__all__ = ["DesktopAgent"]
