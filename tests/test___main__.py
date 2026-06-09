"""Tests for the desktop_use.__main__ CLI entry point."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestMainParser:
    """Tests for argument parsing in __main__.main()."""

    def test_version_flag(self, capsys):
        """--version should print version and exit."""
        from desktop_use.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["desktop-use", "--version"]):
                main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out

    def test_no_command_prints_help(self, capsys):
        """Running with no arguments should print help."""
        from desktop_use.__main__ import main

        with patch("sys.argv", ["desktop-use"]):
            main()

        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "desktop-use" in captured.out.lower()

    def test_serve_sets_env_vars(self):
        """'serve' subcommand should set DESKTOP_USE_* env vars."""
        import os

        from desktop_use.__main__ import main

        with patch("sys.argv", ["desktop-use", "serve", "--host", "127.0.0.1", "--port", "9999", "--ws-port", "9998"]):
            # Mock the server.main to avoid actually starting it
            with patch("desktop_use.server.main") as mock_server:
                try:
                    main()
                except Exception:
                    pass  # server_main is mocked so it returns immediately

        # After the call, env vars should be set
        assert os.environ.get("DESKTOP_USE_HOST") == "127.0.0.1"
        assert os.environ.get("DESKTOP_USE_HTTP_PORT") == "9999"
        assert os.environ.get("DESKTOP_USE_WS_PORT") == "9998"
