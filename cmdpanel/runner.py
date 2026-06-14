"""
runner.py — Async shell command execution with streaming output.

Runs commands in a subprocess without opening an external terminal.
Output (stdout + stderr) is streamed line-by-line via a GLib idle callback.
"""

import subprocess
import threading
from typing import Callable


def run_command(
    command: str,
    on_line: Callable[[str], None],
    on_done: Callable[[bool], None],
):
    """
    Run `command` in a bash shell asynchronously.

    on_line(text)  — called for each line of stdout/stderr (on GLib main thread)
    on_done(ok)    — called when the process finishes; ok=True means exit code 0
    """
    import gi
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib

    def _idle(fn, *args):
        GLib.idle_add(fn, *args)

    def _worker():
        try:
            proc = subprocess.Popen(
                ["bash", "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in proc.stdout:
                line = line.rstrip("\n")
                _idle(on_line, line)
            proc.wait()
            _idle(on_done, proc.returncode == 0)
        except Exception as exc:
            _idle(on_line, f"[error] {exc}")
            _idle(on_done, False)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
