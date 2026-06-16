#!/usr/bin/env python3
"""
desktop_use.server - Desktop Automation HTTP Server
=====================================================

A FastAPI-based server providing desktop automation capabilities on Windows.

Features:
    - Screenshots (full screen or region-based) via mss
    - OCR using RapidOCR ONNX (Chinese + English)
    - OpenCV template matching (find icons/buttons by image)
    - Mouse input: click, double-click, right-click, move, drag
    - Keyboard input: type (clipboard paste), hotkey, press, scroll
    - Window management: focus, resize, move, list
    - Clipboard read/write via PowerShell
    - Batch command execution
    - WebSocket real-time bidirectional communication
    - Health check endpoint

Ports:
    - HTTP API:   8765
    - WebSocket:  8766

Usage:
    python -m desktop_use.server
    desktop-use serve

Environment Variables:
    DESKTOP_USE_HOST        - Bind address (default: 0.0.0.0)
    DESKTOP_USE_HTTP_PORT   - HTTP port (default: 8765)
    DESKTOP_USE_WS_PORT     - WebSocket port (default: 8766)
    DESKTOP_USE_DATA_DIR    - Data directory for screenshots/templates/logs
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HOST: str = os.environ.get("DESKTOP_USE_HOST", "0.0.0.0")
HTTP_PORT: int = int(os.environ.get("DESKTOP_USE_HTTP_PORT", "8765"))
WS_PORT: int = int(os.environ.get("DESKTOP_USE_WS_PORT", "8766"))

_DATA_DIR = Path(os.environ.get("DESKTOP_USE_DATA_DIR", Path.home() / "desktop-use"))
SCREENSHOT_DIR: Path = _DATA_DIR / "screenshots"
TEMPLATE_DIR: Path = _DATA_DIR / "templates"
LOG_FILE: Path = _DATA_DIR / "desktop_use.log"

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
log = logging.getLogger("desktop_use")

# ---------------------------------------------------------------------------
# Dependency imports
# ---------------------------------------------------------------------------


def _import_optional(name: str, pip_hint: str = ""):
    """Import a module by name, logging success or warning on failure."""
    try:
        return __import__(name)
    except ImportError:
        hint = pip_hint or f"pip install {name}"
        log.warning("Optional dependency %s not available (%s)", name, hint)
        return None


pyautogui = _import_optional("pyautogui")
if pyautogui:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

mss_lib = _import_optional("mss")
mss_tools = None
if mss_lib:
    mss_tools = _import_optional("mss.tools")

gw = _import_optional("pygetwindow", "pip install pygetwindow")

PIL_Image = None
try:
    from PIL import Image as PIL_Image
except ImportError:
    log.warning("Pillow not available (pip install pillow)")

# Optional: RapidOCR
ocr_engine = None
try:
    from rapidocr_onnxruntime import RapidOCR

    ocr_engine = RapidOCR()
    log.info("RapidOCR engine initialised")
except Exception as exc:
    log.warning("RapidOCR unavailable: %s", exc)

def _prewarm_ocr():
    """Run a dummy OCR call to load model weights into memory."""
    if ocr_engine is None:
        return
    try:
        dummy = numpy.zeros((64, 200, 3), dtype=numpy.uint8)
        ocr_engine(dummy)
        log.info("OCR engine warmed up")
    except Exception as exc:
        log.warning("OCR warm-up failed: %s", exc)



# Optional: OpenCV
cv2 = _import_optional("cv2", "pip install opencv-python")

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

_start_time: float = time.time()

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def encode_screenshot(
    img_array: numpy.ndarray,
    fmt: str = "JPEG",
    quality: int = 80,
    scale: float = 1.0,
) -> tuple:
    """Convert numpy array to compressed base64 string.
    Returns (base64_string, (width, height)).
    """
    rgb = img_array[:, :, :3][:, :, ::-1]  # BGRA -> RGB
    img = PIL_Image.fromarray(rgb)

    if scale != 1.0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), PIL_Image.LANCZOS)

    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, format="JPEG", quality=quality, optimize=True)
    elif fmt == "WEBP":
        img.save(buf, format="WEBP", quality=quality, method=4)
    else:
        img.save(buf, format="PNG", optimize=True)

    encoded = base64.b64encode(buf.getvalue()).decode()
    return encoded, (img.width, img.height)



def uptime() -> float:
    """Return server uptime in seconds."""
    return round(time.time() - _start_time, 1)


def _powershell(command: str, *, timeout: int = 5) -> str:
    """Run a PowerShell command and return stdout, stripped."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.stdout.strip()
    except Exception as exc:
        log.error("PowerShell error: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------


def clipboard_set(text: str) -> None:
    """Write text to the Windows clipboard via PowerShell.

    This approach bypasses IME issues that occur with direct keyboard input.
    """
    escaped = text.replace("'", "''")
    _powershell(f"Set-Clipboard -Value '{escaped}'")
    time.sleep(0.1)


def clipboard_get() -> str:
    """Read the current Windows clipboard contents."""
    return _powershell("Get-Clipboard")


def clipboard_type(text: str) -> None:
    """Type *text* by pasting from clipboard (Ctrl+V).

    This is the recommended way to input text on Windows because it bypasses
    Input Method Editor (IME) complications and is significantly faster for
    long strings.
    """
    clipboard_set(text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


class ScreenshotEngine:
    """Capture screenshots using mss (fast, cross-platform)."""

    def __init__(self) -> None:
        self._dir = SCREENSHOT_DIR

    def capture(
        self,
        region: Optional[list[int]] = None,
        name: Optional[str] = None,
    ) -> tuple[str, Any]:
        """Capture a screenshot.

        Args:
            region: Optional [x, y, width, height] tuple.  ``None`` captures
                the entire primary monitor.
            name:   Filename to save as (inside the screenshot directory).
                Auto-generated from a timestamp if not provided.

        Returns:
            A tuple of ``(filepath, PIL.Image)``.
        """
        if name is None:
            name = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = str(self._dir / name)

        if mss_lib is None:
            raise RuntimeError("mss is not installed — cannot capture screenshots")

        with mss_lib.mss() as sct:
            if region:
                monitor = {
                    "left": region[0],
                    "top": region[1],
                    "width": region[2],
                    "height": region[3],
                }
            else:
                monitor = sct.monitors[1]
            img = sct.grab(monitor)
            mss_tools.to_png(img.rgb, img.size, output=filepath)

        pil_img = PIL_Image.open(filepath) if PIL_Image else None
        return filepath, pil_img

    def capture_b64(self, region: Optional[list[int]] = None) -> str:
        """Capture a screenshot and return it as a base64-encoded PNG string."""
        _, img = self.capture(region)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()


screenshot_engine = ScreenshotEngine()

# ---------------------------------------------------------------------------
# OCR (RapidOCR)
# ---------------------------------------------------------------------------


class OCREngine:
    """Optical character recognition using RapidOCR ONNX."""

    def ocr_image(self, image_path: str) -> list[dict[str, Any]]:
        """Run OCR on a saved image file.

        Returns:
            List of dicts, each with keys:
                ``text``, ``confidence``, ``center`` [x, y],
                ``bbox`` [x1, y1, x2, y2].
        """
        if ocr_engine is None:
            raise RuntimeError("RapidOCR is not available")

        result, _ = ocr_engine(image_path)
        if not result:
            return []

        items: list[dict[str, Any]] = []
        for line in result:
            box, text, confidence = line
            cx = sum(p[0] for p in box) / len(box)
            cy = sum(p[1] for p in box) / len(box)
            x1 = min(p[0] for p in box)
            y1 = min(p[1] for p in box)
            x2 = max(p[0] for p in box)
            y2 = max(p[1] for p in box)
            items.append(
                {
                    "text": text,
                    "confidence": round(confidence, 3),
                    "center": [int(cx), int(cy)],
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                }
            )
        return items

    def ocr_screen(
        self, region: Optional[list[int]] = None
    ) -> list[dict[str, Any]]:
        """Capture the screen (optionally a region) and OCR it immediately."""
        filepath, _ = screenshot_engine.capture(region)
        return self.ocr_image(filepath)

    def find_text(
        self, target: str, region: Optional[list[int]] = None
    ) -> Optional[dict[str, Any]]:
        """Search for *target* text on screen, return the best match or None."""
        items = self.ocr_screen(region)
        target_lower = target.lower()
        matches = [i for i in items if target_lower in i["text"].lower()]
        return matches[0] if matches else None

    def find_all_text(
        self, target: str, region: Optional[list[int]] = None
    ) -> list[dict[str, Any]]:
        """Return all on-screen occurrences matching *target*."""
        items = self.ocr_screen(region)
        target_lower = target.lower()
        return [i for i in items if target_lower in i["text"].lower()]


ocr = OCREngine()

# ---------------------------------------------------------------------------
# Template matching (OpenCV)
# ---------------------------------------------------------------------------


class TemplateEngine:
    """Find sub-images on screen using OpenCV template matching."""

    def find(
        self,
        template_path: str,
        *,
        screenshot_path: Optional[str] = None,
        threshold: float = 0.8,
        region: Optional[list[int]] = None,
    ) -> Optional[dict[str, Any]]:
        """Find the best match of *template_path* on screen.

        Args:
            template_path:  Filesystem path to the template image.
            screenshot_path: Optional pre-captured screenshot.  If ``None``
                a fresh screenshot is taken.
            threshold:      Minimum match confidence (0–1).
            region:         Screen region to search in (only used when
                *screenshot_path* is not provided).

        Returns:
            ``{center, bbox, confidence}`` or ``None``.
        """
        if cv2 is None:
            raise RuntimeError("OpenCV is not installed — template matching unavailable")

        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            raise FileNotFoundError(f"Cannot read template image: {template_path}")

        if screenshot_path:
            screenshot = cv2.imread(screenshot_path, cv2.IMREAD_COLOR)
        else:
            filepath, _ = screenshot_engine.capture(region)
            screenshot = cv2.imread(filepath, cv2.IMREAD_COLOR)

        if screenshot is None:
            raise RuntimeError("Failed to capture or read screenshot")

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return None

        th, tw = template.shape[:2]
        x, y = max_loc
        return {
            "center": [x + tw // 2, y + th // 2],
            "bbox": [x, y, x + tw, y + th],
            "confidence": round(max_val, 4),
        }

    def find_all(
        self,
        template_path: str,
        *,
        screenshot_path: Optional[str] = None,
        threshold: float = 0.8,
        region: Optional[list[int]] = None,
    ) -> list[dict[str, Any]]:
        """Find **all** instances of *template_path* on screen.

        Matches closer than half the template size are de-duplicated.
        """
        if cv2 is None:
            raise RuntimeError("OpenCV is not installed")

        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            raise FileNotFoundError(f"Cannot read template image: {template_path}")

        if screenshot_path:
            screenshot = cv2.imread(screenshot_path, cv2.IMREAD_COLOR)
        else:
            filepath, _ = screenshot_engine.capture(region)
            screenshot = cv2.imread(filepath, cv2.IMREAD_COLOR)

        if screenshot is None:
            raise RuntimeError("Failed to capture or read screenshot")

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        th, tw = template.shape[:2]

        locations = numpy.where(result >= threshold)
        if len(locations[0]) == 0:
            return []

        items: list[dict[str, Any]] = []
        used: set[tuple[int, int]] = set()
        for pt_y, pt_x in zip(*locations):
            if any(
                abs(pt_x - ux) < tw // 2 and abs(pt_y - uy) < th // 2
                for ux, uy in used
            ):
                continue
            used.add((pt_x, pt_y))
            items.append(
                {
                    "center": [int(pt_x + tw // 2), int(pt_y + th // 2)],
                    "bbox": [int(pt_x), int(pt_y), int(pt_x + tw), int(pt_y + th)],
                    "confidence": round(float(result[pt_y, pt_x]), 4),
                }
            )
        return items


template_engine = TemplateEngine()

# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------


class WindowManager:
    """Manage visible windows via pygetwindow."""

    def _find_window(self, title_keyword: str):
        """Return the first visible window whose title contains *title_keyword*."""
        keyword = title_keyword.lower()
        for w in gw.getAllWindows():
            if w.visible and keyword in w.title.lower():
                return w
        return None

    def focus(self, title_keyword: str) -> tuple[bool, str]:
        """Bring a window to the foreground by title keyword (case-insensitive).

        Returns ``(success, description)``.
        """
        w = self._find_window(title_keyword)
        if w is None:
            return False, f"Window not found: {title_keyword}"

        try:
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.3)
            return True, w.title
        except Exception:
            pyautogui.hotkey("alt", "tab")
            time.sleep(0.5)
            return True, f"Alt-tabbed ({w.title})"

    def list_all(self) -> list[dict[str, Any]]:
        """Return a list of all visible windows with their geometry."""
        return [
            {
                "title": w.title,
                "left": w.left,
                "top": w.top,
                "width": w.width,
                "height": w.height,
                "active": w.isActive,
            }
            for w in gw.getAllWindows()
            if w.visible and w.title
        ]

    def get_active(self) -> dict[str, Any]:
        """Return info about the currently active (focused) window."""
        try:
            w = gw.getActiveWindow()
            return {"title": w.title if w else "Unknown"}
        except Exception:
            return {"title": "Unknown"}

    def resize(self, title_keyword: str, width: int, height: int) -> tuple[bool, str]:
        """Resize a window by title keyword."""
        w = self._find_window(title_keyword)
        if w is None:
            return False, f"Window not found: {title_keyword}"
        try:
            w.resizeTo(width, height)
            return True, f"Resized {w.title} to {width}x{height}"
        except Exception as exc:
            return False, str(exc)

    def move(self, title_keyword: str, x: int, y: int) -> tuple[bool, str]:
        """Move a window by title keyword."""
        w = self._find_window(title_keyword)
        if w is None:
            return False, f"Window not found: {title_keyword}"
        try:
            w.moveTo(x, y)
            return True, f"Moved {w.title} to ({x}, {y})"
        except Exception as exc:
            return False, str(exc)


window_manager = WindowManager()

# ---------------------------------------------------------------------------
# PostMessage input isolation (click/type without moving cursor)
# ---------------------------------------------------------------------------

import ctypes
import ctypes.wintypes

_user32 = ctypes.windll.user32

def _find_hwnd(title_contains: str):
    """Find a window handle by partial title match."""
    import win32gui
    result = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_contains.lower() in title.lower():
                result.append(hwnd)
        return True
    win32gui.EnumWindows(callback, None)
    return result[0] if result else None


def _screen_to_client(hwnd: int, screen_x: int, screen_y: int):
    """Convert screen coordinates to window-relative coordinates."""
    pt = ctypes.wintypes.POINT(screen_x, screen_y)
    _user32.ScreenToClient(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def post_click(hwnd: int, x: int, y: int, button: str = "left", double: bool = False):
    """Click at screen coordinates inside window hwnd.
    Cursor does NOT move. Window does NOT need focus.
    """
    import win32gui
    import win32con
    import win32api

    cx, cy = _screen_to_client(hwnd, x, y)
    lparam = win32api.MAKELONG(cx, cy)

    if button == "left":
        down_msg = win32con.WM_LBUTTONDOWN
        up_msg = win32con.WM_LBUTTONUP
        wparam = win32con.MK_LBUTTON
    elif button == "right":
        down_msg = win32con.WM_RBUTTONDOWN
        up_msg = win32con.WM_RBUTTONUP
        wparam = win32con.WM_RBUTTON
    else:
        down_msg = win32con.WM_MBUTTONDOWN
        up_msg = win32con.WM_MBUTTONUP
        wparam = win32con.WM_MBUTTON

    win32gui.PostMessage(hwnd, down_msg, wparam, lparam)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, up_msg, 0, lparam)

    if double:
        time.sleep(0.08)
        win32gui.PostMessage(hwnd, down_msg, wparam, lparam)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, up_msg, 0, lparam)


def post_type(hwnd: int, text: str):
    """Type text into a window without focusing it.
    Uses clipboard paste (handles Unicode, Chinese, Vietnamese).
    """
    import win32gui
    import win32con

    # Set clipboard via PowerShell
    escaped = text.replace('"', '`"')
    _powershell(f'Set-Clipboard -Value \"{escaped}\"')
    time.sleep(0.1)

    # Send Ctrl+V to the window
    post_hotkey(hwnd, "v", ctrl=True)


def post_hotkey(hwnd: int, key: str, ctrl: bool = False, shift: bool = False, alt: bool = False):
    """Send a hotkey combination to a window without focusing it."""
    import win32gui
    import win32con

    VK_MAP = {
        "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
        "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
        "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
        "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
        "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
        "z": 0x5A, "enter": 0x0D, "tab": 0x09, "escape": 0x1B,
        "delete": 0x2E, "backspace": 0x08,
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
        "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    }
    vk = VK_MAP.get(key.lower(), ord(key.upper()))

    def _lparam(vk_code, extended=False):
        scan = _user32.MapVirtualKeyW(vk_code, 0)
        lp = (scan << 16) | 1
        if extended:
            lp |= (1 << 24)
        return lp

    # Press modifiers
    if ctrl:
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, _lparam(win32con.VK_CONTROL))
    if shift:
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_SHIFT, _lparam(win32con.VK_SHIFT))
    if alt:
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_MENU, _lparam(win32con.VK_MENU))

    # Press key
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, _lparam(vk))
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, _lparam(vk) | (1 << 30) | (1 << 31))

    # Release modifiers (reverse order)
    if alt:
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_MENU, _lparam(win32con.VK_MENU) | (1 << 31))
    if shift:
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_SHIFT, _lparam(win32con.VK_SHIFT) | (1 << 31))
    if ctrl:
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, _lparam(win32con.VK_CONTROL) | (1 << 31))


def post_scroll(hwnd: int, x: int, y: int, amount: int):
    """Scroll at a position in a window. amount: positive=up, negative=down."""
    import win32gui
    import win32con
    import win32api

    # WM_MOUSEWHEEL uses screen coords, not client coords
    lparam = win32api.MAKELONG(x, y)
    wparam = win32api.MAKELONG(0, amount * win32con.WHEEL_DELTA)
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)



# ---------------------------------------------------------------------------
# Command executor
# ---------------------------------------------------------------------------


def _resolve_template(path: str) -> str:
    """Resolve a template path, falling back to the templates directory."""
    if os.path.isabs(path):
        return path
    return str(TEMPLATE_DIR / path)


def execute_command(cmd: dict[str, Any]) -> dict[str, Any]:
    """Execute a single automation command and return the result.

    Supported actions:
        Screenshots:  ``screenshot``, ``ocr``, ``find_text``, ``find_all_text``
        Templates:    ``find_template``, ``find_all_templates``
        Windows:      ``focus_window``, ``get_windows``, ``get_active``,
                      ``resize_window``, ``move_window``
        Mouse:        ``click``, ``double_click``, ``right_click``,
                      ``move``, ``drag``, ``get_mouse``
        Keyboard:     ``type``, ``hotkey``, ``press``, ``scroll``
        Clipboard:    ``clipboard_set``, ``clipboard_get``
        Utility:      ``get_screen_size``, ``wait``, ``batch``

    Args:
        cmd: A dict with at least an ``"action"`` key.

    Returns:
        A dict with ``"success"`` (bool) and either ``"data"`` or ``"error"``.
    """
    action = cmd.get("action", "")
    try:
        # ── Screenshots ────────────────────────────────────────────────────
        if action == "screenshot":
            region = cmd.get("region")
            name = cmd.get("name")
            filepath, _ = screenshot_engine.capture(region, name)
            result: dict[str, Any] = {"success": True, "path": filepath}

            if cmd.get("ocr") and ocr_engine is not None:
                result["ocr"] = ocr.ocr_image(filepath)

            if cmd.get("base64"):
                with open(filepath, "rb") as f:
                    result["base64"] = base64.b64encode(f.read()).decode()

            return result

        # ── OCR ────────────────────────────────────────────────────────────
        elif action == "ocr":
            img_path = cmd.get("path")
            region = cmd.get("region")
            data = ocr.ocr_image(img_path) if img_path else ocr.ocr_screen(region)
            return {"success": True, "data": data, "count": len(data)}

        elif action == "find_text":
            match = ocr.find_text(cmd["text"], cmd.get("region"))
            if match:
                return {"success": True, "data": match}
            return {"success": False, "error": f"Text not found: {cmd['text']}"}

        elif action == "find_all_text":
            matches = ocr.find_all_text(cmd["text"], cmd.get("region"))
            return {"success": True, "data": matches, "count": len(matches)}

        # ── Template matching ──────────────────────────────────────────────
        elif action == "find_template":
            tpl = _resolve_template(cmd["template"])
            match = template_engine.find(
                tpl,
                threshold=cmd.get("threshold", 0.8),
                region=cmd.get("region"),
            )
            if match:
                return {"success": True, "data": match}
            return {"success": False, "error": "Template not found"}

        elif action == "find_all_templates":
            tpl = _resolve_template(cmd["template"])
            matches = template_engine.find_all(
                tpl,
                threshold=cmd.get("threshold", 0.8),
                region=cmd.get("region"),
            )
            return {"success": True, "data": matches, "count": len(matches)}

        # ── Window management ──────────────────────────────────────────────
        elif action == "focus_window":
            found, title = window_manager.focus(cmd["title"])
            return {"success": found, "data": title}

        elif action == "get_windows":
            return {"success": True, "data": window_manager.list_all()}

        elif action == "get_active":
            return {"success": True, "data": window_manager.get_active()}

        elif action == "resize_window":
            ok, msg = window_manager.resize(
                cmd["title"], cmd["width"], cmd["height"]
            )
            return {"success": ok, "data": msg}

        elif action == "move_window":
            ok, msg = window_manager.move(cmd["title"], cmd["x"], cmd["y"])
            return {"success": ok, "data": msg}

        # ── Mouse ──────────────────────────────────────────────────────────
        elif action == "click":
            x, y, button = cmd["x"], cmd["y"], cmd.get("button", "left")
            win_title = cmd.get("window_title")
            if win_title:
                hwnd = _find_hwnd(win_title)
                if hwnd:
                    post_click(hwnd, x, y, button)
                    return {"success": True, "data": f"PostMessage click ({x}, {y}) on {win_title}"}
            pyautogui.click(x, y, button=button)
            return {"success": True, "data": f"Clicked ({x}, {y})"}

        elif action == "double_click":
            x, y = cmd["x"], cmd["y"]
            win_title = cmd.get("window_title")
            if win_title:
                hwnd = _find_hwnd(win_title)
                if hwnd:
                    post_click(hwnd, x, y, "left", double=True)
                    return {"success": True, "data": f"PostMessage double-click ({x}, {y}) on {win_title}"}
            pyautogui.doubleClick(x, y)
            return {"success": True, "data": f"Double-clicked ({x}, {y})"}

        elif action == "right_click":
            x, y = cmd["x"], cmd["y"]
            win_title = cmd.get("window_title")
            if win_title:
                hwnd = _find_hwnd(win_title)
                if hwnd:
                    post_click(hwnd, x, y, "right")
                    return {"success": True, "data": f"PostMessage right-click ({x}, {y}) on {win_title}"}
            pyautogui.rightClick(x, y)
            return {"success": True, "data": f"Right-clicked ({x}, {y})"}

        elif action == "move":
            pyautogui.moveTo(
                cmd["x"], cmd["y"], duration=cmd.get("duration", 0.3)
            )
            return {
                "success": True,
                "data": f"Moved to ({cmd['x']}, {cmd['y']})",
            }

        elif action == "drag":
            pyautogui.moveTo(cmd["x1"], cmd["y1"])
            pyautogui.drag(
                cmd["x2"] - cmd["x1"],
                cmd["y2"] - cmd["y1"],
                duration=cmd.get("duration", 0.5),
            )
            return {"success": True, "data": "Dragged"}

        elif action == "get_mouse":
            pos = pyautogui.position()
            return {"success": True, "data": {"x": pos[0], "y": pos[1]}}

        # ── Keyboard ───────────────────────────────────────────────────────
        elif action == "type":
            win_title = cmd.get("window_title")
            if win_title:
                hwnd = _find_hwnd(win_title)
                if hwnd:
                    post_type(hwnd, cmd["text"])
                    return {"success": True, "data": f"PostMessage type on {win_title}"}
            clipboard_type(cmd["text"])
            return {"success": True, "data": "Typed via clipboard paste"}

        elif action == "hotkey":
            keys = cmd["keys"]
            win_title = cmd.get("window_title")
            if win_title:
                hwnd = _find_hwnd(win_title)
                if hwnd:
                    post_hotkey(hwnd, keys[-1], ctrl="ctrl" in keys, shift="shift" in keys, alt="alt" in keys)
                    return {"success": True, "data": f"PostMessage hotkey {'+'.join(keys)} on {win_title}"}
            pyautogui.hotkey(*keys)
            return {"success": True, "data": f"Pressed {'+'.join(keys)}"}

        elif action == "press":
            pyautogui.press(cmd["key"], presses=cmd.get("presses", 1))
            return {"success": True, "data": f"Pressed {cmd['key']}"}

        elif action == "scroll":
            amount = cmd["amount"]
            x, y = cmd.get("x"), cmd.get("y")
            if x is not None and y is not None:
                pyautogui.scroll(amount, x=x, y=y)
            else:
                pyautogui.scroll(amount)
            return {"success": True, "data": f"Scrolled {amount}"}

        # ── Clipboard ──────────────────────────────────────────────────────
        elif action == "clipboard_set":
            clipboard_set(cmd["text"])
            return {"success": True, "data": "Clipboard set"}

        elif action == "clipboard_get":
            return {"success": True, "data": clipboard_get()}

        # ── Screen info ────────────────────────────────────────────────────
        elif action == "get_screen_size":
            size = pyautogui.size()
            return {"success": True, "data": {"width": size[0], "height": size[1]}}

        # ── Utility ────────────────────────────────────────────────────────
        elif action == "wait":
            time.sleep(cmd["seconds"])
            return {"success": True, "data": f"Waited {cmd['seconds']}s"}

        elif action == "batch":
            results: list[dict[str, Any]] = []
            for c in cmd["commands"]:
                r = execute_command(c)
                results.append({"cmd": c.get("action"), "result": r})
                if not r.get("success"):
                    break
                time.sleep(0.1)
            return {"success": True, "data": results}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except pyautogui.FailSafeException:
        log.warning("FAILSAFE triggered (mouse moved to screen corner)")
        return {"success": False, "error": "FAILSAFE — mouse moved to corner"}
    except Exception as exc:
        log.error("Command '%s' error: %s", action, exc)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# FastAPI HTTP application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="desktop_use",
    description="Desktop automation HTTP server",
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health-check endpoint.

    Returns server status, uptime, and feature availability.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime": uptime(),
        "ocr": ocr_engine is not None,
        "opencv": cv2 is not None,
        "pid": os.getpid(),
    }


@app.post("/action")
async def action(cmd: dict[str, Any]) -> JSONResponse:
    """Execute a single automation command.

    Request body: ``{"action": "<name>", ...action-specific fields...}``

    See :func:`execute_command` for the list of supported actions.
    """
    result = execute_command(cmd)
    return JSONResponse(content=result)


@app.post("/batch")
async def batch(body: dict[str, Any]) -> JSONResponse:
    """Execute multiple commands sequentially.

    Request body: ``{"commands": [{...}, {...}, ...]}``

    Execution stops at the first failed command.
    """
    results: list[dict[str, Any]] = []
    for cmd in body.get("commands", []):
        r = execute_command(cmd)
        results.append({"cmd": cmd.get("action"), "result": r})
        if not r.get("success"):
            break
        await asyncio.sleep(0.05)
    return JSONResponse(content={"success": True, "data": results})


@app.get("/screenshot")
async def api_screenshot(
    region: Optional[str] = None,
    ocr_flag: bool = False,
    base64_out: bool = False,
) -> JSONResponse:
    """Capture a screenshot.

    Query parameters:
        region:     Comma-separated ``x,y,w,h`` for a screen region.
        ocr_flag:   If true, run OCR on the captured image.
        base64_out: If true, include the image as a base64 string.
    """
    r = [int(x) for x in region.split(",")] if region else None
    filepath, _ = screenshot_engine.capture(r)
    result: dict[str, Any] = {"success": True, "path": filepath}

    if ocr_flag and ocr_engine is not None:
        result["ocr"] = ocr.ocr_image(filepath)

    if base64_out:
        with open(filepath, "rb") as f:
            result["base64"] = base64.b64encode(f.read()).decode()

    return JSONResponse(content=result)


@app.get("/windows")
async def api_windows() -> dict[str, Any]:
    """List all visible windows with their positions and sizes."""
    return {"success": True, "data": window_manager.list_all()}


@app.get("/mouse")
async def api_mouse() -> dict[str, Any]:
    """Return the current mouse cursor position."""
    pos = pyautogui.position()
    return {"success": True, "data": {"x": pos[0], "y": pos[1]}}


@app.get("/screen_size")
async def api_screen_size() -> dict[str, Any]:
    """Return the primary monitor resolution."""
    size = pyautogui.size()
    return {"success": True, "data": {"width": size[0], "height": size[1]}}


# ---------------------------------------------------------------------------
# WebSocket server
# ---------------------------------------------------------------------------

ws_clients: list[WebSocket] = []


async def ws_handler(websocket: WebSocket) -> None:
    """Handle a WebSocket connection.

    Clients send JSON-encoded commands and receive JSON responses.
    Long-running commands are executed in a thread pool to avoid blocking
    the event loop.
    """
    await websocket.accept()
    ws_clients.append(websocket)
    log.info("WebSocket client connected (%d total)", len(ws_clients))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"success": False, "error": "Invalid JSON"}
                )
                continue

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, execute_command, cmd)
            await websocket.send_json(result)

    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        log.info("WebSocket client disconnected (%d total)", len(ws_clients))
    except Exception as exc:
        log.error("WebSocket error: %s", exc)
        if websocket in ws_clients:
            ws_clients.remove(websocket)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _run_ws_server() -> None:
    """Run the WebSocket server in a background thread."""
    import threading

    def _thread() -> None:
        async def _start() -> None:
            import websockets as ws_lib

            server = await ws_lib.serve(ws_handler, HOST, WS_PORT)
            log.info("WebSocket server ready on ws://%s:%d", HOST, WS_PORT)
            await server.wait_closed()

        asyncio.run(_start())

    t = threading.Thread(target=_thread, daemon=True)
    t.start()


def main() -> None:
    """Start the desktop_use server (HTTP + WebSocket)."""
    log.info("=" * 60)
    log.info("  desktop_use server v0.1.0")
    log.info("  HTTP API:     http://%s:%d", HOST, HTTP_PORT)
    log.info("  WebSocket:    ws://%s:%d", HOST, WS_PORT)
    log.info("  Data dir:     %s", _DATA_DIR)
    log.info("  Templates:    %s", TEMPLATE_DIR)
    log.info("  RapidOCR:     %s", "ON" if ocr_engine else "OFF")
    log.info("  OpenCV:       %s", "ON" if cv2 is not None else "OFF")
    log.info("  FAILSAFE:     move mouse to top-left corner to abort")
    log.info("=" * 60)

    # Warm up OCR engine and take initial screenshot
    _prewarm_ocr()
    try:
        screenshot_engine.capture(name="initial_screen.png")
    except Exception as exc:
        log.warning("Could not take initial screenshot: %s", exc)

    # Start WebSocket server in a background thread
    _run_ws_server()

    # Start HTTP server (blocking — main thread)
    uvicorn.run(app, host=HOST, port=HTTP_PORT, log_level="info")


if __name__ == "__main__":
    main()
