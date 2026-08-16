"""Shared async subprocess runner for integration scripts."""

import asyncio
import sys
from pathlib import Path


async def run_python_script(
    *,
    logger,
    script_path: Path,
    script_name: str,
    timeout_seconds: int,
    log_prefix: str,
    env: dict[str, str] | None = None,
    args: list[str] | None = None,
) -> None:
    """Execute a Python script and log outcome consistently."""
    if not script_path.exists():
        logger.error("%s script not found: %s", log_prefix, script_path)
        return

    run_args = args or []

    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            *run_args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error("%s script timed out after %ss: %s", log_prefix, timeout_seconds, script_name)
        return
    except Exception as err:
        logger.error("%s script failed to launch (%s): %s", log_prefix, script_name, err)
        return

    out = (stdout or b"").decode("utf-8", errors="replace").strip()
    err = (stderr or b"").decode("utf-8", errors="replace").strip()

    if process.returncode == 0:
        logger.info("%s script succeeded: %s", log_prefix, script_name)
        if out:
            logger.info("[%s stdout] %s", script_name, out)
        return

    logger.error("%s script failed (%s) rc=%s", log_prefix, script_name, process.returncode)
    if out:
        logger.error("[%s stdout] %s", script_name, out)
    if err:
        logger.error("[%s stderr] %s", script_name, err)
