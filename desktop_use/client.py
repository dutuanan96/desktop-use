#!/usr/bin/env python3
"""
Desktop Agent Client
====================
WSL/CLI client for the Desktop Agent HTTP API server.

Connects to the server running on Windows (localhost:8765) and provides
a clean Python API for desktop automation: screenshots, OCR, mouse/keyboard
control, window management, clipboard, and batch operations.

Usage as a library:
    from desktop_use.client import DesktopAgent

    agent = DesktopAgent()
    agent.click(100, 200)
    agent.type_text("Hello, World!")
    result = agent.find_text("Submit")
    if result["success"]:
        agent.click(*result["data"]["center"])

Usage from CLI:
    python -m desktop_use.client screenshot
    python -m desktop_use.client click 100 200
    python -m desktop_use.client find_text "Submit"
    python -m desktop_use.client health

Requirements:
    pip install requests
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Optional, Union

try:
    import requests
except ImportError:
    print("Error: 'requests' is required. Install with: pip install requests")
    sys.exit(1)


class DesktopConnectionError(Exception):
    """Raised when desktop-use server is unreachable."""
    pass


class TextNotFoundError(Exception):
    """Raised when text is not found on screen."""
    pass


# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8765
DEFAULT_TIMEOUT = 30  # seconds


def _win_to_wsl(win_path: str) -> str:
    """Convert a Windows path to its WSL equivalent.

    Example: ``C:\\Users\\hp\\Desktop\\shot.png`` -> ``/mnt/c/Users/hp/Desktop/shot.png``

    Args:
        win_path: A Windows-style path (e.g. ``C:\\Users\\...``).

    Returns:
        The equivalent WSL path, or the original string if conversion is not
        applicable.
    """
    if not win_path or len(win_path) < 2 or win_path[1] != ":":
        return win_path
    drive = win_path[0].lower()
    rest = win_path[2:].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


# ── DesktopAgent ──────────────────────────────────────────────────────────────

class DesktopAgent:
    """Client for the Desktop Agent HTTP API server.

    All methods return a ``dict`` with at least a ``"success"`` key.
    On error the dict contains ``"error"`` with a human-readable message.

    Args:
        host: Hostname or IP of the server (default ``localhost``).
        port: Port of the HTTP API (default ``8765``).
        timeout: HTTP request timeout in seconds (default ``30``).
        server_url: Full base URL override (e.g. ``http://192.168.1.5:8765``).
                    If provided, *host* and *port* are ignored.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        server_url: str | None = None,
    ) -> None:
        if server_url:
            self.base_url = server_url.rstrip("/")
        else:
            self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"DesktopAgent(url={self.base_url!r})"

    # ── Low-level transport ───────────────────────────────────────────────

    def _post(self, action: str, **kwargs: Any) -> dict[str, Any]:
        """Send a command to the server via HTTP POST ``/action``.

        Args:
            action: The action name (e.g. ``"click"``, ``"screenshot"``).
            **kwargs: Additional parameters forwarded as the JSON body.

        Returns:
            Server response as a dict.

        Raises:
            DesktopConnectionError: If server is unreachable.
        """
        payload: dict[str, Any] = {"action": action, **kwargs}
        try:
            resp = requests.post(
                f"{self.base_url}/action",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            raise DesktopConnectionError(
                f"Cannot reach desktop-use server at {self.base_url}. "
                "Is it running on Windows? Run: desktop-use serve"
            )
        except requests.Timeout:
            raise DesktopConnectionError(
                f"Server timed out after {self.timeout}s. "
                "OCR/template matching can be slow - try increasing timeout."
            )
        except DesktopConnectionError:
            raise
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        """Send a GET request to the server.

        Args:
            endpoint: The endpoint path (e.g. ``"health"``, ``"windows"``).
            **params: Query parameters.

        Returns:
            Server response as a dict.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            return {"success": False, "error": "Server is not running"}
        except requests.Timeout:
            return {"success": False, "error": f"Request timed out after {self.timeout}s"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── Health ────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Check server health and capabilities.

        Returns:
            ``{"status": "ok", "version": ..., "ocr": bool, "opencv": bool, ...}``
        """
        return self._get("health")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass  # No resources to clean up

    # ── Screenshot ────────────────────────────────────────────────────────

    def screenshot(
        self,
        region: list[int] | None = None,
        ocr: bool = False,
        save_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Take a screenshot.

        Args:
            region: ``[x, y, width, height]`` to capture a sub-region,
                    or ``None`` for the full screen.
            ocr: If ``True``, run OCR on the screenshot and include results.
            save_path: If provided, copy the screenshot to this local path.

        Returns:
            ``{"success": True, "path": "<win_path>", "wsl_path": "<wsl_path>",
              "ocr": [...], "local_path": "<save_path>"}``
        """
        kwargs: dict[str, Any] = {"ocr": ocr}
        if region is not None:
            kwargs["region"] = region
        result = self._post("screenshot", **kwargs)

        if result.get("success") and result.get("path"):
            wsl_path = _win_to_wsl(result["path"])
            result["wsl_path"] = wsl_path
            if save_path:
                shutil.copy2(wsl_path, str(save_path))
                result["local_path"] = str(save_path)

        return result

    def screenshot_base64(self, region: list[int] | None = None) -> str:
        """Take a screenshot and return the raw PNG as a base64 string.

        Args:
            region: ``[x, y, width, height]`` or ``None`` for full screen.

        Returns:
            Base64-encoded PNG string (empty string on failure).
        """
        kwargs: dict[str, Any] = {"base64": True}
        if region is not None:
            kwargs["region"] = region
        result = self._post("screenshot", **kwargs)
        return result.get("base64", "")

    # ── OCR ───────────────────────────────────────────────────────────────

    def ocr(
        self,
        path: str | None = None,
        region: list[int] | None = None,
    ) -> dict[str, Any]:
        """Run OCR on an image file or a screen region.

        If neither *path* nor *region* is given, OCR is run on the full screen.

        Args:
            path: Windows path to an image file.
            region: ``[x, y, width, height]`` screen region to capture and OCR.

        Returns:
            ``{"success": True, "data": [{"text", "confidence", "center", "bbox"}, ...],
              "count": int}``
        """
        kwargs: dict[str, Any] = {}
        if path is not None:
            kwargs["path"] = path
        if region is not None:
            kwargs["region"] = region
        return self._post("ocr", **kwargs)

    # ── Find text ─────────────────────────────────────────────────────────

    def find_text(
        self,
        text: str,
        region: list[int] | None = None,
    ) -> dict[str, Any]:
        """Find text on screen and return the best match.

        Args:
            text: The text substring to search for (case-insensitive).
            region: Optional ``[x, y, width, height]`` to limit the search area.

        Returns:
            ``{"success": True, "data": {"text", "confidence", "center", "bbox"}}``
            or ``{"success": False, "error": "Text not found: ..."}``
        """
        kwargs: dict[str, Any] = {"text": text}
        if region is not None:
            kwargs["region"] = region
        return self._post("find_text", **kwargs)

    def find_all_text(
        self,
        text: str,
        region: list[int] | None = None,
    ) -> dict[str, Any]:
        """Find all occurrences of text on screen.

        Args:
            text: The text substring to search for (case-insensitive).
            region: Optional ``[x, y, width, height]`` to limit the search area.

        Returns:
            ``{"success": True, "data": [...], "count": int}``
        """
        kwargs: dict[str, Any] = {"text": text}
        if region is not None:
            kwargs["region"] = region
        return self._post("find_all_text", **kwargs)

    # ── Template matching ─────────────────────────────────────────────────

    def find_template(
        self,
        template: str,
        threshold: float = 0.8,
        region: list[int] | None = None,
    ) -> dict[str, Any]:
        """Find a template image on screen using OpenCV matching.

        Args:
            template: Filename (relative to the server's templates dir) or
                      absolute Windows path to the template image.
            threshold: Minimum match confidence (0.0 – 1.0, default 0.8).
            region: Optional ``[x, y, width, height]`` to limit the search area.

        Returns:
            ``{"success": True, "data": {"center", "bbox", "confidence"}}``
            or ``{"success": False, "error": "Template not found"}``
        """
        kwargs: dict[str, Any] = {"template": template, "threshold": threshold}
        if region is not None:
            kwargs["region"] = region
        return self._post("find_template", **kwargs)

    def find_all_templates(
        self,
        template: str,
        threshold: float = 0.8,
        region: list[int] | None = None,
    ) -> dict[str, Any]:
        """Find all instances of a template image on screen.

        Args:
            template: Filename or absolute path to the template image.
            threshold: Minimum match confidence (0.0 – 1.0).
            region: Optional ``[x, y, width, height]``.

        Returns:
            ``{"success": True, "data": [...], "count": int}``
        """
        kwargs: dict[str, Any] = {"template": template, "threshold": threshold}
        if region is not None:
            kwargs["region"] = region
        return self._post("find_all_templates", **kwargs)

    # ── Mouse ─────────────────────────────────────────────────────────────

    def click(self, x: int, y: int, button: str = "left", window_title: str | None = None) -> dict[str, Any]:
        """Click at the given coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            button: ``"left"``, ``"right"``, or ``"middle"``.
            window_title: If provided, use PostMessage (cursor doesn't move).
        """
        kwargs: dict[str, Any] = {"x": x, "y": y, "button": button}
        if window_title:
            kwargs["window_title"] = window_title
        return self._post("click", **kwargs)

    def double_click(self, x: int, y: int, window_title: str | None = None) -> dict[str, Any]:
        """Double-click at the given coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            window_title: If provided, use PostMessage (cursor doesn't move).
        """
        kwargs: dict[str, Any] = {"x": x, "y": y}
        if window_title:
            kwargs["window_title"] = window_title
        return self._post("double_click", **kwargs)

    def right_click(self, x: int, y: int, window_title: str | None = None) -> dict[str, Any]:
        """Right-click at the given coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            window_title: If provided, use PostMessage (cursor doesn't move).
        """
        kwargs: dict[str, Any] = {"x": x, "y": y}
        if window_title:
            kwargs["window_title"] = window_title
        return self._post("right_click", **kwargs)

    def move(self, x: int, y: int, duration: float = 0.3) -> dict[str, Any]:
        """Move the mouse cursor to the given coordinates.

        Args:
            x: Target horizontal pixel coordinate.
            y: Target vertical pixel coordinate.
            duration: Time in seconds for the movement animation.
        """
        return self._post("move", x=x, y=y, duration=duration)

    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.5,
    ) -> dict[str, Any]:
        """Drag from (x1, y1) to (x2, y2).

        Args:
            x1: Start horizontal coordinate.
            y1: Start vertical coordinate.
            x2: End horizontal coordinate.
            y2: End vertical coordinate.
            duration: Time in seconds for the drag animation.
        """
        return self._post("drag", x1=x1, y1=y1, x2=x2, y2=y2, duration=duration)

    def get_mouse(self) -> dict[str, Any]:
        """Get the current mouse cursor position.

        Returns:
            ``{"success": True, "data": {"x": int, "y": int}}``
        """
        return self._post("get_mouse")

    # ── Keyboard ──────────────────────────────────────────────────────────

    def type_text(self, text: str, window_title: str | None = None) -> dict[str, Any]:
        """Type text using clipboard paste (bypasses IME for Chinese etc.).

        The text is placed on the Windows clipboard and then pasted with
        ``Ctrl+V``. This works around input method editor (IME) issues
        that prevent direct ``pyautogui.typewrite()`` for non-ASCII text.

        Args:
            text: The string to type.
            window_title: If provided, use PostMessage (cursor doesn't move).
        """
        kwargs: dict[str, Any] = {"text": text}
        if window_title:
            kwargs["window_title"] = window_title
        return self._post("type", **kwargs)

    def hotkey(self, *keys: str, window_title: str | None = None) -> dict[str, Any]:
        """Press a key combination.

        Args:
            *keys: Individual key names, e.g. ``hotkey("ctrl", "c")``.
            window_title: If provided, use PostMessage (cursor doesn't move).
        """
        kwargs: dict[str, Any] = {"keys": list(keys)}
        if window_title:
            kwargs["window_title"] = window_title
        return self._post("hotkey", **kwargs)

    def press(self, key: str, presses: int = 1) -> dict[str, Any]:
        """Press a single key one or more times.

        Args:
            key: Key name (e.g. ``"enter"``, ``"f5"``, ``"space"``).
            presses: Number of times to press the key.
        """
        return self._post("press", key=key, presses=presses)

    def scroll(
        self,
        amount: int,
        x: int | None = None,
        y: int | None = None,
    ) -> dict[str, Any]:
        """Scroll the mouse wheel.

        Args:
            amount: Positive scrolls up, negative scrolls down.
            x: Optional horizontal position to scroll at.
            y: Optional vertical position to scroll at.
        """
        kwargs: dict[str, Any] = {"amount": amount}
        if x is not None:
            kwargs["x"] = x
        if y is not None:
            kwargs["y"] = y
        return self._post("scroll", **kwargs)

    # ── Window management ─────────────────────────────────────────────────

    def focus_window(self, title: str) -> dict[str, Any]:
        """Find and focus a window by title keyword (case-insensitive).

        Args:
            title: Substring to match against window titles.

        Returns:
            ``{"success": True, "data": "<matched_title>"}``
        """
        return self._post("focus_window", title=title)

    def get_windows(self) -> dict[str, Any]:
        """List all visible windows.

        Returns:
            ``{"success": True, "data": [{"title", "left", "top", "width",
            "height", "active"}, ...]}``
        """
        return self._get("windows")

    def get_active(self) -> dict[str, Any]:
        """Get the currently active (focused) window.

        Returns:
            ``{"success": True, "data": {"title": str}}``
        """
        return self._post("get_active")

    def resize_window(self, title: str, width: int, height: int) -> dict[str, Any]:
        """Resize a window by title keyword.

        Args:
            title: Substring to match against window titles.
            width: New width in pixels.
            height: New height in pixels.
        """
        return self._post("resize_window", title=title, width=width, height=height)

    def move_window(self, title: str, x: int, y: int) -> dict[str, Any]:
        """Move a window by title keyword.

        Args:
            title: Substring to match against window titles.
            x: New left edge coordinate.
            y: New top edge coordinate.
        """
        return self._post("move_window", title=title, x=x, y=y)

    # ── Clipboard ─────────────────────────────────────────────────────────

    def clipboard_set(self, text: str) -> dict[str, Any]:
        """Set the Windows clipboard content.

        Args:
            text: The text to place on the clipboard.
        """
        return self._post("clipboard_set", text=text)

    def clipboard_get(self) -> str:
        """Get the current Windows clipboard content.

        Returns:
            The clipboard text, or an empty string on failure.
        """
        result = self._post("clipboard_get")
        return result.get("data", "")

    # ── Screen info ───────────────────────────────────────────────────────

    def screen_size(self) -> dict[str, Any]:
        """Get the primary monitor resolution.

        Returns:
            ``{"success": True, "data": {"width": int, "height": int}}``
        """
        return self._get("screen_size")

    # ── Utility ───────────────────────────────────────────────────────────

    def wait(self, seconds: float) -> dict[str, Any]:
        """Ask the server to wait (sleep) for the given duration.

        Useful inside batch commands to insert pauses.

        Args:
            seconds: Time to wait in seconds.
        """
        return self._post("wait", seconds=seconds)

    def batch(self, commands: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute a list of commands sequentially on the server.

        Execution stops at the first failure. A 100 ms delay is inserted
        between commands.

        Args:
            commands: List of command dicts, each with an ``"action"`` key
                      and any required parameters. Example::

                          [
                              {"action": "click", "x": 100, "y": 200},
                              {"action": "type", "text": "hello"},
                              {"action": "press", "key": "enter"},
                          ]

        Returns:
            ``{"success": True, "data": [{"cmd": str, "result": dict}, ...]}``
        """
        return self._post("batch", commands=commands)

    def run_script(self, code: str) -> dict[str, Any]:
        """Execute arbitrary Python code on the server.

        .. warning::

            This is inherently dangerous — only use with trusted code.

        Args:
            code: Python source code string.

        Returns:
            ``{"success": True, "data": "Script executed"}``
        """
        return self._post("run_script", code=code)


# ── CLI ───────────────────────────────────────────────────────────────────────

HELP_TEXT = """\
Desktop Agent Client
====================

Usage:  python -m desktop_use.client <command> [args]

Server:
  --host HOST          Server hostname  (default: localhost)
  --port PORT          Server port      (default: 8765)
  --url URL            Full server URL  (overrides host/port)

Commands:
  health                        Check server health
  screenshot [--ocr] [--save PATH] [--region x,y,w,h]
                                Take a screenshot
  ocr [PATH]                    OCR an image or the screen
  find_text TEXT                 Find text on screen (best match)
  find_all_text TEXT             Find all text matches on screen
  find_template FILE [THRESHOLD] Find a template image on screen
  click X Y                     Left-click at coordinates
  right_click X Y               Right-click at coordinates
  double_click X Y               Double-click at coordinates
  type TEXT                     Type text via clipboard paste
  hotkey KEY [KEY ...]           Press key combination
  press KEY [COUNT]              Press a single key
  scroll AMOUNT                  Scroll (positive=up, negative=down)
  move X Y                       Move mouse cursor
  mouse                          Get mouse position
  screensize                     Get screen resolution
  windows                        List visible windows
  focus TITLE                    Focus a window by title keyword
  clipboard_get                  Read Windows clipboard
  clipboard_set TEXT             Set Windows clipboard
  batch COMMANDS_JSON            Execute a JSON array of commands
"""


def _build_parser() -> Any:
    """Build the CLI argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="desktop-use",
        description="Desktop automation client for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Tip: Use --url http://host:port to connect to a remote server.",
    )
    parser.add_argument("command", nargs="?", default=None, help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--url", default=None, help="Full server URL (overrides host/port)")
    return parser


def _output(data: Any) -> None:
    """Pretty-print JSON output."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cli_main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).
    """
    parser = _build_parser()

    if argv is None:
        argv = sys.argv[1:]

    # Pre-parse for server connection options
    args, remaining = parser.parse_known_args(argv)

    if args.command is None:
        print(HELP_TEXT)
        return

    agent = DesktopAgent(host=args.host, port=args.port, server_url=args.url)
    cmd = args.command
    parts = remaining  # remaining positional-ish args after the command

    try:
        if cmd == "health":
            _output(agent.health())

        elif cmd == "screenshot":
            do_ocr = "--ocr" in parts
            save_path = None
            region = None

            # Parse --save PATH
            if "--save" in parts:
                idx = parts.index("--save")
                if idx + 1 < len(parts):
                    save_path = parts[idx + 1]

            # Parse --region x,y,w,h
            if "--region" in parts:
                idx = parts.index("--region")
                if idx + 1 < len(parts):
                    region = [int(v) for v in parts[idx + 1].split(",")]

            _output(agent.screenshot(ocr=do_ocr, region=region, save_path=save_path))

        elif cmd == "ocr":
            path = parts[0] if parts else None
            _output(agent.ocr(path=path))

        elif cmd == "find_text":
            text = " ".join(parts)
            if not text:
                print("Error: provide text to search for")
                sys.exit(1)
            _output(agent.find_text(text))

        elif cmd == "find_all_text":
            text = " ".join(parts)
            if not text:
                print("Error: provide text to search for")
                sys.exit(1)
            _output(agent.find_all_text(text))

        elif cmd == "find_template":
            if not parts:
                print("Error: provide template filename")
                sys.exit(1)
            template = parts[0]
            threshold = float(parts[1]) if len(parts) > 1 else 0.8
            _output(agent.find_template(template, threshold=threshold))

        elif cmd == "click":
            if len(parts) < 2:
                print("Error: provide X Y coordinates")
                sys.exit(1)
            x, y = int(parts[0]), int(parts[1])
            _output(agent.click(x, y))

        elif cmd == "right_click":
            if len(parts) < 2:
                print("Error: provide X Y coordinates")
                sys.exit(1)
            x, y = int(parts[0]), int(parts[1])
            _output(agent.right_click(x, y))

        elif cmd == "double_click":
            if len(parts) < 2:
                print("Error: provide X Y coordinates")
                sys.exit(1)
            x, y = int(parts[0]), int(parts[1])
            _output(agent.double_click(x, y))

        elif cmd == "type":
            text = " ".join(parts)
            if not text:
                print("Error: provide text to type")
                sys.exit(1)
            _output(agent.type_text(text))

        elif cmd == "hotkey":
            if not parts:
                print("Error: provide at least one key")
                sys.exit(1)
            _output(agent.hotkey(*parts))

        elif cmd == "press":
            if not parts:
                print("Error: provide a key name")
                sys.exit(1)
            key = parts[0]
            presses = int(parts[1]) if len(parts) > 1 else 1
            _output(agent.press(key, presses))

        elif cmd == "scroll":
            if not parts:
                print("Error: provide scroll amount")
                sys.exit(1)
            _output(agent.scroll(int(parts[0])))

        elif cmd == "move":
            if len(parts) < 2:
                print("Error: provide X Y coordinates")
                sys.exit(1)
            x, y = int(parts[0]), int(parts[1])
            _output(agent.move(x, y))

        elif cmd == "mouse":
            _output(agent.get_mouse())

        elif cmd == "screensize":
            _output(agent.screen_size())

        elif cmd == "windows":
            result = agent.get_windows()
            if result.get("success"):
                for w in result.get("data", []):
                    active = " [ACTIVE]" if w.get("active") else ""
                    print(
                        f"  {w['title']}  "
                        f"[{w['width']}x{w['height']}] "
                        f"@ ({w['left']},{w['top']}){active}"
                    )
            else:
                _output(result)

        elif cmd == "focus":
            title = " ".join(parts)
            if not title:
                print("Error: provide window title keyword")
                sys.exit(1)
            _output(agent.focus_window(title))

        elif cmd == "clipboard_get":
            text = agent.clipboard_get()
            print(text)

        elif cmd == "clipboard_set":
            text = " ".join(parts)
            _output(agent.clipboard_set(text))

        elif cmd == "batch":
            raw = " ".join(parts)
            if not raw:
                print("Error: provide a JSON array of commands")
                sys.exit(1)
            commands = json.loads(raw)
            _output(agent.batch(commands))

        elif cmd == "wait":
            if not parts:
                print("Error: provide seconds to wait")
                sys.exit(1)
            _output(agent.wait(float(parts[0])))

        else:
            print(f"Unknown command: {cmd}")
            print("Run with no arguments for help.")
            sys.exit(1)

    except (ValueError, IndexError) as exc:
        print(f"Argument error: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)


# ── Package entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    cli_main()
