"""Tests for desktop_use.server module.

Uses httpx.AsyncClient to test the FastAPI endpoints without starting uvicorn.
Heavy Windows dependencies (pyautogui, mss, pygetwindow, etc.) are stubbed via
conftest._install_mock_modules.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health(app):
    """GET /health should return status ok with feature flags."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime" in body
    assert isinstance(body["ocr"], bool)
    assert isinstance(body["opencv"], bool)
    assert isinstance(body["pid"], int)


# ---------------------------------------------------------------------------
# Action endpoint — dispatch routing
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_action_unknown_action(app):
    """POST /action with an unknown action should return success=False."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "nonexistent"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Unknown action" in body["error"]


@pytest.mark.anyio
async def test_action_missing_action(app):
    """POST /action with empty body should fail gracefully."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False


# ---------------------------------------------------------------------------
# Action endpoint — individual actions
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_action_wait(app):
    """POST /action with 'wait' action should succeed (short duration)."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "wait", "seconds": 0.01})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "0.01s" in body["data"]


@pytest.mark.anyio
async def test_action_get_screen_size(app):
    """POST /action with 'get_screen_size' returns width and height."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "get_screen_size"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "width" in body["data"]
    assert "height" in body["data"]


@pytest.mark.anyio
async def test_action_get_mouse(app):
    """POST /action with 'get_mouse' returns x, y coordinates."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "get_mouse"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "x" in body["data"]
    assert "y" in body["data"]


@pytest.mark.anyio
async def test_action_get_active_window(app):
    """POST /action with 'get_active' returns window title."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "get_active"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "title" in body["data"]


@pytest.mark.anyio
async def test_action_clipboard_get(app):
    """POST /action with 'clipboard_get' returns a string."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "clipboard_get"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], str)


@pytest.mark.anyio
async def test_action_get_windows(app):
    """POST /action with 'get_windows' returns a list."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "get_windows"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Batch endpoint
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_batch_empty(app):
    """POST /batch with empty commands should succeed."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/batch", json={"commands": []})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []


@pytest.mark.anyio
async def test_batch_single_wait(app):
    """POST /batch with a single wait command."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/batch",
            json={"commands": [{"action": "wait", "seconds": 0.01}]},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["cmd"] == "wait"
    assert body["data"][0]["result"]["success"] is True


@pytest.mark.anyio
async def test_batch_stops_on_failure(app):
    """Batch should stop at the first failing command."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/batch",
            json={
                "commands": [
                    {"action": "nonexistent"},
                    {"action": "wait", "seconds": 0.01},
                ]
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # Should only have the failed command (execution stops)
    assert len(body["data"]) == 1
    assert body["data"][0]["result"]["success"] is False


# ---------------------------------------------------------------------------
# Screenshot / OCR actions
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_action_screenshot_fails_without_mss(app):
    """Screenshot without mss should fail gracefully."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/action", json={"action": "screenshot"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "mss" in body["error"].lower() or "not installed" in body["error"].lower()


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def test_resolve_template_absolute():
    """_resolve_template returns absolute paths unchanged."""
    from desktop_use.server import _resolve_template

    result = _resolve_template("/some/absolute/path.png")
    assert result == "/some/absolute/path.png"


def test_resolve_template_relative():
    """_resolve_template resolves relative paths against TEMPLATE_DIR."""
    from desktop_use.server import TEMPLATE_DIR, _resolve_template

    result = _resolve_template("button.png")
    assert str(TEMPLATE_DIR) in result
    assert result.endswith("button.png")


# ---------------------------------------------------------------------------
# Uptime helper
# ---------------------------------------------------------------------------


def test_uptime():
    """uptime() should return a non-negative float."""
    from desktop_use.server import uptime

    u = uptime()
    assert isinstance(u, float)
    assert u >= 0


# ---------------------------------------------------------------------------
# Execute command — unknown action
# ---------------------------------------------------------------------------


def test_execute_command_unknown():
    """execute_command with unknown action returns success=False."""
    from desktop_use.server import execute_command

    result = execute_command({"action": "totally_bogus"})
    assert result["success"] is False
    assert "Unknown action" in result["error"]


# ---------------------------------------------------------------------------
# Execute command — wait
# ---------------------------------------------------------------------------


def test_execute_command_wait():
    """execute_command with 'wait' action sleeps and returns success."""
    from desktop_use.server import execute_command

    result = execute_command({"action": "wait", "seconds": 0.01})
    assert result["success"] is True
    assert "0.01s" in result["data"]


# ---------------------------------------------------------------------------
# CORS / FastAPI config
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_action_endpoint_accepts_json(app):
    """POST /action should accept application/json."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/action",
            json={"action": "wait", "seconds": 0.001},
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
