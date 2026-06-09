"""Tests for desktop_use.client module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWinToWsl:
    """Tests for the _win_to_wsl path conversion utility."""

    def test_convert_standard_path(self):
        from desktop_use.client import _win_to_wsl

        assert _win_to_wsl(r"C:\Users\hp\Desktop\shot.png") == "/mnt/c/Users/hp/Desktop/shot.png"

    def test_convert_d_drive(self):
        from desktop_use.client import _win_to_wsl

        assert _win_to_wsl(r"D:\projects\file.py") == "/mnt/d/projects/file.py"

    def test_non_windows_path_unchanged(self):
        from desktop_use.client import _win_to_wsl

        assert _win_to_wsl("/mnt/c/some/path") == "/mnt/c/some/path"

    def test_empty_string(self):
        from desktop_use.client import _win_to_wsl

        assert _win_to_wsl("") == ""

    def test_short_string(self):
        from desktop_use.client import _win_to_wsl

        assert _win_to_wsl("ab") == "ab"

    def test_no_drive_letter(self):
        from desktop_use.client import _win_to_wsl

        assert _win_to_wsl("relative/path") == "relative/path"


class TestDesktopAgentInit:
    """Tests for DesktopAgent constructor."""

    def test_default_url(self):
        from desktop_use.client import DesktopAgent

        agent = DesktopAgent()
        assert agent.base_url == "http://localhost:8765"
        assert agent.timeout == 30

    def test_custom_host_port(self):
        from desktop_use.client import DesktopAgent

        agent = DesktopAgent(host="192.168.1.10", port=9000)
        assert agent.base_url == "http://192.168.1.10:9000"

    def test_server_url_override(self):
        from desktop_use.client import DesktopAgent

        agent = DesktopAgent(server_url="http://myhost:5555")
        assert agent.base_url == "http://myhost:5555"

    def test_server_url_trailing_slash_stripped(self):
        from desktop_use.client import DesktopAgent

        agent = DesktopAgent(server_url="http://myhost:5555/")
        assert agent.base_url == "http://myhost:5555"


class TestDesktopAgentPost:
    """Tests for the low-level _post transport method."""

    @patch("desktop_use.client.requests.post")
    def test_post_success(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": "ok"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent._post("click", x=100, y=200)

        assert result == {"success": True, "data": "ok"}
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "/action" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["action"] == "click"
        assert call_kwargs[1]["json"]["x"] == 100

    @patch("desktop_use.client.requests.post")
    def test_post_connection_error(self, mock_post):
        import requests as _requests
        from desktop_use.client import DesktopAgent

        mock_post.side_effect = _requests.ConnectionError("refused")

        agent = DesktopAgent()
        result = agent._post("click", x=0, y=0)

        assert result["success"] is False
        assert "not running" in result["error"].lower()

    @patch("desktop_use.client.requests.post", side_effect=__import__("requests").Timeout)
    def test_post_timeout(self, mock_post):
        from desktop_use.client import DesktopAgent

        agent = DesktopAgent(timeout=5)
        result = agent._post("click", x=0, y=0)

        assert result["success"] is False
        assert "timed out" in result["error"].lower()


class TestDesktopAgentGet:
    """Tests for the low-level _get transport method."""

    @patch("desktop_use.client.requests.get")
    def test_get_success(self, mock_get):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok", "version": "1.0.0"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        agent = DesktopAgent()
        result = agent._get("health")

        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"

    @patch("desktop_use.client.requests.get", side_effect=ConnectionError)
    def test_get_connection_error(self, mock_get):
        from desktop_use.client import DesktopAgent

        agent = DesktopAgent()
        result = agent._get("windows")

        assert result["success"] is False


class TestDesktopAgentHighLevel:
    """Tests for high-level client methods (screenshot, mouse, keyboard, etc.)."""

    @patch("desktop_use.client.requests.post")
    def test_click(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": "Clicked (10, 20)"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.click(10, 20)

        assert result["success"] is True
        body = mock_post.call_args[1]["json"]
        assert body["action"] == "click"
        assert body["x"] == 10
        assert body["y"] == 20
        assert body["button"] == "left"

    @patch("desktop_use.client.requests.post")
    def test_double_click(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.double_click(50, 60)

        assert result["success"] is True
        body = mock_post.call_args[1]["json"]
        assert body["action"] == "double_click"

    @patch("desktop_use.client.requests.post")
    def test_right_click(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.right_click(50, 60)

        assert result["success"] is True
        body = mock_post.call_args[1]["json"]
        assert body["action"] == "right_click"

    @patch("desktop_use.client.requests.post")
    def test_move(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.move(100, 200, duration=0.5)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "move"
        assert body["x"] == 100
        assert body["y"] == 200
        assert body["duration"] == 0.5

    @patch("desktop_use.client.requests.post")
    def test_drag(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.drag(10, 20, 30, 40)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "drag"
        assert body["x1"] == 10
        assert body["y2"] == 40

    @patch("desktop_use.client.requests.post")
    def test_type_text(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.type_text("Hello World")

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "type"
        assert body["text"] == "Hello World"

    @patch("desktop_use.client.requests.post")
    def test_hotkey(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.hotkey("ctrl", "c")

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "hotkey"
        assert body["keys"] == ["ctrl", "c"]

    @patch("desktop_use.client.requests.post")
    def test_press(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.press("enter", presses=3)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "press"
        assert body["key"] == "enter"
        assert body["presses"] == 3

    @patch("desktop_use.client.requests.post")
    def test_scroll(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.scroll(-3)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "scroll"
        assert body["amount"] == -3

    @patch("desktop_use.client.requests.post")
    def test_scroll_with_position(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.scroll(5, x=100, y=200)

        body = mock_post.call_args[1]["json"]
        assert body["x"] == 100
        assert body["y"] == 200

    @patch("desktop_use.client.requests.post")
    def test_find_text(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {"text": "Submit"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.find_text("Submit")

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "find_text"
        assert body["text"] == "Submit"

    @patch("desktop_use.client.requests.post")
    def test_find_template(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {"center": [50, 50]}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.find_template("button.png", threshold=0.9)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "find_template"
        assert body["template"] == "button.png"
        assert body["threshold"] == 0.9

    @patch("desktop_use.client.requests.post")
    def test_focus_window(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": "Notepad"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.focus_window("notepad")

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "focus_window"
        assert body["title"] == "notepad"

    @patch("desktop_use.client.requests.post")
    def test_batch(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        commands = [
            {"action": "click", "x": 10, "y": 20},
            {"action": "type", "text": "hello"},
        ]
        agent.batch(commands)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "batch"
        assert len(body["commands"]) == 2

    @patch("desktop_use.client.requests.post")
    def test_clipboard_set(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.clipboard_set("my text")

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "clipboard_set"
        assert body["text"] == "my text"

    @patch("desktop_use.client.requests.post")
    def test_clipboard_get(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": "clipboard content"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.clipboard_get()

        assert result == "clipboard content"
        body = mock_post.call_args[1]["json"]
        assert body["action"] == "clipboard_get"

    @patch("desktop_use.client.requests.get")
    def test_screen_size(self, mock_get):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {"width": 1920, "height": 1080}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.screen_size()

        assert result["data"]["width"] == 1920
        assert result["data"]["height"] == 1080
        assert "/screen_size" in mock_get.call_args[0][0]

    @patch("desktop_use.client.requests.get")
    def test_get_windows(self, mock_get):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": [{"title": "Notepad"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.get_windows()

        assert result["success"] is True
        assert "/windows" in mock_get.call_args[0][0]

    @patch("desktop_use.client.requests.post")
    def test_wait(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.wait(2.5)

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "wait"
        assert body["seconds"] == 2.5

    @patch("desktop_use.client.requests.post")
    def test_run_script(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        agent.run_script("print('hello')")

        body = mock_post.call_args[1]["json"]
        assert body["action"] == "run_script"
        assert body["code"] == "print('hello')"

    @patch("desktop_use.client.requests.post")
    def test_get_mouse(self, mock_post):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {"x": 500, "y": 300}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.get_mouse()

        assert result["data"]["x"] == 500
        assert result["data"]["y"] == 300
        body = mock_post.call_args[1]["json"]
        assert body["action"] == "get_mouse"

    @patch("desktop_use.client.requests.get")
    def test_health(self, mock_get):
        from desktop_use.client import DesktopAgent

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok", "ocr": True}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        agent = DesktopAgent()
        result = agent.health()

        assert result["status"] == "ok"
        assert "/health" in mock_get.call_args[0][0]
