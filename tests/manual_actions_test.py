"""Failure-path tests for Telegram manual actions."""

from pathlib import Path

import pytest

import integrations.manual_actions as manual_actions


class _Process:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    async def communicate(self):
        return self.stdout, self.stderr


@pytest.mark.asyncio
async def test_run_manual_action_rejects_unknown_action():
    ok, message = await manual_actions.run_manual_action("does-not-exist")

    assert not ok
    assert "Unknown action" in message


@pytest.mark.asyncio
async def test_run_manual_action_reports_missing_script(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(manual_actions, "SCRIPTS_DIR", tmp_path)

    ok, message = await manual_actions.run_manual_action("plex_check_summary")

    assert not ok
    assert "Script not found" in message


@pytest.mark.asyncio
async def test_run_manual_action_reports_nonzero_output(tmp_path: Path, monkeypatch):
    script = tmp_path / "check_plex_titles.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(manual_actions, "SCRIPTS_DIR", tmp_path)

    async def _create_process(*args, **kwargs):
        return _Process(2, b"partial output", b"failure details")

    monkeypatch.setattr(manual_actions.asyncio, "create_subprocess_exec", _create_process)

    ok, message = await manual_actions.run_manual_action("plex_check_summary")

    assert not ok
    assert "Exit code:* `2`" in message
    assert "partial output" in message
    assert "failure details" in message


@pytest.mark.asyncio
async def test_run_manual_action_reports_timeout(tmp_path: Path, monkeypatch):
    script = tmp_path / "check_plex_titles.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(manual_actions, "SCRIPTS_DIR", tmp_path)
    monkeypatch.setattr(manual_actions, "MANUAL_ACTION_TIMEOUT", 4)

    async def _create_process(*args, **kwargs):
        return _Process(0)

    async def _wait_for(coro, timeout):
        coro.close()
        raise manual_actions.asyncio.TimeoutError()

    monkeypatch.setattr(manual_actions.asyncio, "create_subprocess_exec", _create_process)
    monkeypatch.setattr(manual_actions.asyncio, "wait_for", _wait_for)

    ok, message = await manual_actions.run_manual_action("plex_check_summary")

    assert not ok
    assert "timed out after 4s" in message


@pytest.mark.asyncio
async def test_run_manual_action_reports_launch_failure(tmp_path: Path, monkeypatch):
    script = tmp_path / "check_plex_titles.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(manual_actions, "SCRIPTS_DIR", tmp_path)

    async def _create_process(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(manual_actions.asyncio, "create_subprocess_exec", _create_process)

    ok, message = await manual_actions.run_manual_action("plex_check_summary")

    assert not ok
    assert "Failed to run" in message
    assert "permission denied" in message
