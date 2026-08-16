"""Unit tests for shared script runner."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from integrations.script_runner import run_python_script


class _Proc:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_run_python_script_missing_file_logs_error(tmp_path: Path):
    logger = MagicMock()
    missing = tmp_path / "missing.py"

    await run_python_script(
        logger=logger,
        script_path=missing,
        script_name="missing.py",
        timeout_seconds=1,
        log_prefix="Radarr",
    )

    logger.error.assert_called_once()
    assert "script not found" in logger.error.call_args.args[0]


@pytest.mark.asyncio
async def test_run_python_script_timeout_logs_error(tmp_path: Path, monkeypatch):
    logger = MagicMock()
    script = tmp_path / "ok.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    async def _fake_create_subprocess_exec(*args, **kwargs):
        return _Proc(returncode=0)

    async def _fake_wait_for(coro, timeout):
        coro.close()
        raise TimeoutError()

    monkeypatch.setattr(
        "integrations.script_runner.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )
    monkeypatch.setattr("integrations.script_runner.asyncio.wait_for", _fake_wait_for)

    await run_python_script(
        logger=logger,
        script_path=script,
        script_name="ok.py",
        timeout_seconds=3,
        log_prefix="Sonarr",
    )

    logger.error.assert_called_once()
    assert "timed out" in logger.error.call_args.args[0]


@pytest.mark.asyncio
async def test_run_python_script_launch_failure_logs_error(tmp_path: Path, monkeypatch):
    logger = MagicMock()
    script = tmp_path / "ok.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    launch_error = OSError("executable unavailable")

    async def _fake_create_subprocess_exec(*args, **kwargs):
        raise launch_error

    monkeypatch.setattr(
        "integrations.script_runner.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )

    await run_python_script(
        logger=logger,
        script_path=script,
        script_name="ok.py",
        timeout_seconds=3,
        log_prefix="Sonarr",
    )

    logger.error.assert_called_once_with(
        "%s script failed to launch (%s): %s",
        "Sonarr",
        "ok.py",
        launch_error,
    )


@pytest.mark.asyncio
async def test_run_python_script_success_logs_info(tmp_path: Path, monkeypatch):
    logger = MagicMock()
    script = tmp_path / "ok.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    async def _fake_create_subprocess_exec(*args, **kwargs):
        return _Proc(returncode=0, stdout=b"done\n")

    async def _fake_wait_for(coro, timeout):
        return await coro

    monkeypatch.setattr(
        "integrations.script_runner.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )
    monkeypatch.setattr("integrations.script_runner.asyncio.wait_for", _fake_wait_for)

    await run_python_script(
        logger=logger,
        script_path=script,
        script_name="ok.py",
        timeout_seconds=3,
        log_prefix="Tautulli",
    )

    logger.info.assert_any_call("%s script succeeded: %s", "Tautulli", "ok.py")
    logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_run_python_script_failure_logs_stdout_and_stderr(tmp_path: Path, monkeypatch):
    logger = MagicMock()
    script = tmp_path / "bad.py"
    script.write_text("print('bad')\n", encoding="utf-8")

    async def _fake_create_subprocess_exec(*args, **kwargs):
        return _Proc(returncode=2, stdout=b"bad out", stderr=b"bad err")

    async def _fake_wait_for(coro, timeout):
        return await coro

    monkeypatch.setattr(
        "integrations.script_runner.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )
    monkeypatch.setattr("integrations.script_runner.asyncio.wait_for", _fake_wait_for)

    await run_python_script(
        logger=logger,
        script_path=script,
        script_name="bad.py",
        timeout_seconds=3,
        log_prefix="Radarr",
    )

    logger.error.assert_any_call("%s script failed (%s) rc=%s", "Radarr", "bad.py", 2)
    logger.error.assert_any_call("[%s stdout] %s", "bad.py", "bad out")
    logger.error.assert_any_call("[%s stderr] %s", "bad.py", "bad err")
