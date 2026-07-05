#!/usr/bin/env python3
"""
picat-mcp-server
================

A small Model Context Protocol (MCP) server that exposes a single tool,
``run_picat``, for executing Picat source code.

Requirements
------------
* Python 3.10+
* The `mcp` Python SDK:  ``pip install "mcp[cli]"``
* The Picat interpreter installed and on your PATH, or pointed at via
  ``--picat-path`` / the ``PICAT_PATH`` environment variable.
  Download Picat from: http://picat-lang.org/

Running
-------
Run as a stdio MCP server (the default transport for local tools)::

    python picat_mcp_server.py
    python picat_mcp_server.py --picat-path /opt/picat/picat --default-timeout 60

Claude Desktop / Claude Code ``mcpServers`` entry::

    {
      "picat": {
        "command": "python",
        "args": ["/absolute/path/to/picat_mcp_server.py"],
        "env": { "PICAT_PATH": "/opt/picat/picat" }
      }
    }

Example tool call from an MCP client
------------------------------------
The agent invokes the ``run_picat`` tool with::

    code = '''
    main =>
        N = 10,
        F is fib(N),
        printf("fib(%w) = %w%n", N, F).

    table
    fib(0) = 0.
    fib(1) = 1.
    fib(N) = F => N > 1, F = fib(N - 1) + fib(N - 2).
    '''

and receives back the program's stdout, stderr, exit code, and timing.

Security note
-------------
This server executes arbitrary user-supplied Picat code on the host machine.
Only run it in environments you trust, or wrap execution in a sandbox
(container, firejail, nsjail, etc.). Treat the tool the same way you would
treat a shell tool.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_BYTES = 200_000  # truncate combined stdout+stderr above this size


def _resolve_picat_binary(explicit: Optional[str]) -> str:
    """Return the path to the picat binary or raise FileNotFoundError."""
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        # Maybe the explicit value is a bare name that lives on PATH.
        on_path = shutil.which(explicit)
        if on_path:
            return on_path
        raise FileNotFoundError(
            f"Picat binary not found at {explicit!r}. "
            "Install Picat from http://picat-lang.org/ and pass --picat-path "
            "or set the PICAT_PATH environment variable."
        )
    on_path = shutil.which("picat")
    if on_path:
        return on_path
    raise FileNotFoundError(
        "The `picat` interpreter was not found on PATH. "
        "Install Picat from http://picat-lang.org/ and pass --picat-path "
        "or set the PICAT_PATH environment variable."
    )


# ---------------------------------------------------------------------------
# Core execution logic (decoupled from MCP so it can be unit-tested)
# ---------------------------------------------------------------------------


@dataclass
class PicatResult:
    """Structured outcome of a single Picat invocation."""

    ok: bool
    exit_code: Optional[int]
    duration_ms: int
    timed_out: bool
    stdout: str
    stderr: str
    command: str
    error: Optional[str] = None

    def to_text(self) -> str:
        """Render a human-readable report suitable for an LLM tool response."""
        lines = [
            f"Picat run: {'OK' if self.ok else 'FAILED'}",
            f"command:      {self.command}",
            f"exit_code:    {self.exit_code if self.exit_code is not None else 'n/a'}",
            f"duration_ms:  {self.duration_ms}",
            f"timed_out:    {self.timed_out}",
        ]
        if self.error:
            lines.append(f"error:        {self.error}")
        if self.stderr:
            lines.append("")
            lines.append("--- stderr ---")
            lines.append(self.stderr.rstrip("\n"))
        lines.append("")
        lines.append("--- stdout ---")
        lines.append(self.stdout.rstrip("\n"))
        return "\n".join(lines)


def _truncate(text: str, max_bytes: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    cut = raw[:max_bytes].decode("utf-8", errors="ignore")
    return cut + f"\n... [truncated, {len(raw) - max_bytes} bytes omitted]"


def run_picat_source(
    code: str,
    *,
    args: Optional[list[str]] = None,
    timeout: Optional[float] = None,
    picat_path: str,
) -> PicatResult:
    """Execute Picat ``code`` by writing it to a temp file and invoking picat.

    The ``args`` list is passed on the picat command line and becomes the
    ``Args`` list inside a ``main(Args) => ...`` clause in Picat.
    """
    args = list(args or [])
    if timeout is None:
        timeout = DEFAULT_TIMEOUT_SECONDS

    # Picat loads a source file. We use the conventional ``.pi`` extension.
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".pi", encoding="utf-8", delete=False
    )
    try:
        tmp.write(code)
        tmp.flush()
        tmp.close()

        cmd = [picat_path, tmp.name, *args]

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            partial_out = e.stdout if isinstance(e.stdout, str) else ""
            partial_err = e.stderr if isinstance(e.stderr, str) else ""
            return PicatResult(
                ok=False,
                exit_code=None,
                duration_ms=elapsed_ms,
                timed_out=True,
                stdout=partial_out or "",
                stderr=partial_err or "",
                command=" ".join(cmd),
                error=f"Timed out after {timeout}s",
            )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        # Keep responses reasonable for LLM context windows.
        if (
            len(stdout.encode("utf-8")) + len(stderr.encode("utf-8"))
            > MAX_OUTPUT_BYTES
        ):
            half = MAX_OUTPUT_BYTES // 2
            stdout = _truncate(stdout, half)
            stderr = _truncate(stderr, half)

        return PicatResult(
            ok=(proc.returncode == 0),
            exit_code=proc.returncode,
            duration_ms=elapsed_ms,
            timed_out=False,
            stdout=stdout,
            stderr=stderr,
            command=" ".join(cmd),
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# MCP server (FastMCP)
# ---------------------------------------------------------------------------

mcp = FastMCP("picat-mcp-server")

# Module-level config populated from argparse/env in main(); the tool reads it.
_CONFIG: dict[str, Any] = {
    "picat_path": None,
    "default_timeout": DEFAULT_TIMEOUT_SECONDS,
}


@mcp.tool()
def run_picat(
    code: str,
    args: Optional[list[str]] = None,
    timeout: Optional[float] = None,
) -> str:
    """Run Picat source code and return stdout, stderr, exit code, and timing.

    Parameters
    ----------
    code:
        The Picat source code to execute. Include a ``main =>`` or
        ``main(Args) =>`` clause as the entry point, e.g.::

            main =>
                println(hello_world),
                F = fib(10),
                printf("fib(10) = %w%n", F).

            table
            fib(0) = 0.
            fib(1) = 1.
            fib(N) = F => N > 1, F = fib(N-1) + fib(N-2).

        Without a ``main`` clause, Picat loads the file but typically produces
        no output and exits.
    args:
        Optional list of command-line arguments forwarded to the Picat program.
        Inside Picat these arrive as ``Args`` in a ``main(Args) => ...`` clause.
        Example: args=["5", "10"].
    timeout:
        Maximum wall-clock seconds to allow the program to run before it is
        killed. Defaults to the server's configured default (30s, override with
        --default-timeout or PICAT_DEFAULT_TIMEOUT).

    Returns
    -------
    A human-readable text report containing the command that was run, the exit
    code, the elapsed time, whether the run timed out, and the program's stdout
    and stderr.
    """
    try:
        picat_path = _resolve_picat_binary(_CONFIG["picat_path"])
    except FileNotFoundError as e:
        return PicatResult(
            ok=False,
            exit_code=None,
            duration_ms=0,
            timed_out=False,
            stdout="",
            stderr="",
            command="",
            error=str(e),
        ).to_text()

    if timeout is None:
        timeout = _CONFIG["default_timeout"]

    result = run_picat_source(
        code,
        args=args,
        timeout=timeout,
        picat_path=picat_path,
    )
    return result.to_text()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="picat-mcp-server",
        description="A small MCP server exposing a `run_picat` tool.",
    )
    p.add_argument(
        "--picat-path",
        default=os.environ.get("PICAT_PATH"),
        help="Path to the picat binary (defaults to $PICAT_PATH or PATH lookup).",
    )
    p.add_argument(
        "--default-timeout",
        type=float,
        default=float(
            os.environ.get("PICAT_DEFAULT_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)
        ),
        help="Default per-run timeout in seconds (default: %(default)s).",
    )
    p.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio"],
        help="MCP transport (only stdio is supported for now).",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    ns = _build_arg_parser().parse_args(argv)
    _CONFIG["picat_path"] = ns.picat_path
    _CONFIG["default_timeout"] = ns.default_timeout

    # Fail-fast diagnostic at startup; the server still starts so a client can
    # connect and receive a clear error from the tool itself.
    try:
        resolved = _resolve_picat_binary(_CONFIG["picat_path"])
        print(f"[picat-mcp-server] using picat at: {resolved}", file=sys.stderr)
    except FileNotFoundError as e:
        print(f"[picat-mcp-server] WARNING: {e}", file=sys.stderr)
        print(
            "[picat-mcp-server] The server will still start, but `run_picat` "
            "calls will fail until Picat is installed/configured.",
            file=sys.stderr,
        )

    mcp.run(transport=ns.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
