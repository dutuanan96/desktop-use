"""Shared fixtures for desktop_use tests."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


def _install_mock_modules() -> None:
    """Install lightweight stubs for Windows-only modules before any import of
    desktop_use.server, which eagerly imports them at module level.
    """
    # pyautogui mock with the attributes server.py accesses
    pa_mod = types.ModuleType("pyautogui")
    pa_mod.FAILSAFE = True
    pa_mod.PAUSE = 0.05
    pa_mod.FailSafeException = type("FailSafeException", (Exception,), {})
    pa_mod.size = MagicMock(return_value=(1920, 1080))
    pa_mod.position = MagicMock(return_value=(500, 300))
    pa_mod.click = MagicMock()
    pa_mod.doubleClick = MagicMock()
    pa_mod.rightClick = MagicMock()
    pa_mod.moveTo = MagicMock()
    pa_mod.drag = MagicMock()
    pa_mod.hotkey = MagicMock()
    pa_mod.press = MagicMock()
    pa_mod.scroll = MagicMock()

    # pygetwindow mock
    gw_mod = types.ModuleType("pygetwindow")
    gw_mod.getAllWindows = MagicMock(return_value=[])
    gw_mod.getActiveWindow = MagicMock(return_value=MagicMock(title="TestWindow"))

    stubs = {
        "pyautogui": pa_mod,
        "mss": types.ModuleType("mss"),
        "mss.tools": types.ModuleType("mss.tools"),
        "pygetwindow": gw_mod,
        "rapidocr_onnxruntime": types.ModuleType("rapidocr_onnxruntime"),
    }

    for name, mod in stubs.items():
        if name not in sys.modules:
            # Handle sub-modules like mss.tools
            parts = name.rsplit(".", 1)
            if len(parts) == 2:
                parent_name = parts[0]
                parent = sys.modules.get(parent_name)
                if parent is None:
                    parent = types.ModuleType(parent_name)
                    sys.modules[parent_name] = parent
                setattr(parent, parts[1], mod)
            sys.modules[name] = mod


# Ensure stubs exist before any test module imports desktop_use.server
_install_mock_modules()


@pytest.fixture
def client():
    """Return a DesktopAgent pointed at a dummy server."""
    from desktop_use.client import DesktopAgent

    return DesktopAgent(host="127.0.0.1", port=19999)


@pytest.fixture
def app():
    """Return the FastAPI ``app`` from the server module.

    Heavy imports are guarded by the mock stubs installed above.
    """
    # Re-import after mocks are in place
    from desktop_use.server import app as _app

    return _app
