#!/usr/bin/env python3
"""
cmdpaneld — CmdPanel DBus daemon

Exposes the well-known name  io.github.cmdpanel.Daemon  on the session bus.
The GNOME Shell extension talks to this daemon for all persistence and
subprocess execution — keeping the extension itself free of blocking calls.

DBus interface (io.github.cmdpanel.Daemon):
  GetCommands()           → JSON string of saved commands
  SaveCommands(json)      → persist the full list
  RunCommand(command_id)  → start a job; returns job_id string
  signal JobLine(job_id, line)
  signal JobDone(job_id, ok)

Auto-started by the session bus when the extension first calls any method.
"""

import sys
import os
import json
import uuid
import subprocess
import threading
import signal
import logging


def _ensure_gi_typelib_path():
    """
    Discover girepository dirs and add to GI_TYPELIB_PATH without
    hardcoding any path.
    """
    import glob
    candidates = (
        glob.glob("/usr/lib*/girepository-1.0")
        + glob.glob("/usr/local/lib*/girepository-1.0")
    )
    existing = set(p for p in os.environ.get("GI_TYPELIB_PATH", "").split(":") if p)
    additions = [p for p in candidates if p not in existing and os.path.isdir(p)]
    if additions:
        os.environ["GI_TYPELIB_PATH"] = ":".join(list(existing) + additions)


_ensure_gi_typelib_path()

import gi
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")
from gi.repository import GLib, Gio

from cmdpanel.store import load_commands, save_commands

logging.basicConfig(
    level=logging.INFO,
    format="[cmdpaneld] %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("cmdpaneld")

# ── DBus interface XML ────────────────────────────────────────────────────────

DBUS_NAME  = "io.github.cmdpanel.Daemon"
DBUS_PATH  = "/io/github/cmdpanel/Daemon"
DBUS_IFACE = "io.github.cmdpanel.Daemon"

IFACE_XML = f"""
<node>
  <interface name="{DBUS_IFACE}">
    <method name="GetCommands">
      <arg direction="out" type="s" name="json"/>
    </method>
    <method name="SaveCommands">
      <arg direction="in" type="s" name="json"/>
    </method>
    <method name="RunCommand">
      <arg direction="in"  type="s" name="command_id"/>
      <arg direction="out" type="s" name="job_id"/>
    </method>
    <signal name="JobLine">
      <arg type="s" name="job_id"/>
      <arg type="s" name="line"/>
    </signal>
    <signal name="JobDone">
      <arg type="s" name="job_id"/>
      <arg type="b" name="ok"/>
    </signal>
  </interface>
</node>
"""

# ── Service implementation ────────────────────────────────────────────────────

class CmdPanelDaemon(Gio.Application):
    """
    Gio.Application with IS_SERVICE flag — owns the well-known DBus name
    and exits cleanly when the session bus releases it.
    """

    def __init__(self):
        super().__init__(
            application_id=DBUS_NAME,
            flags=Gio.ApplicationFlags.IS_SERVICE,
        )
        self._conn      = None
        self._reg_id    = None
        self._node_info = Gio.DBusNodeInfo.new_for_xml(IFACE_XML)
        self._iface     = self._node_info.interfaces[0]
        self._commands  = load_commands()
        self._jobs: dict[str, subprocess.Popen] = {}

    # ── Gio.Application hooks ─────────────────────────────────────────────────

    def do_dbus_register(self, conn, object_path):
        self._conn   = conn
        self._reg_id = conn.register_object(
            DBUS_PATH,
            self._iface,
            self._on_method_call,
            None,
            None,
        )
        log.info("registered at %s", DBUS_PATH)
        return True

    def do_dbus_unregister(self, conn, object_path):
        if self._reg_id:
            conn.unregister_object(self._reg_id)
            self._reg_id = None

    # ── Method dispatch ───────────────────────────────────────────────────────

    def _on_method_call(self, conn, sender, path, iface, method, params, invocation):
        try:
            if method == "GetCommands":
                invocation.return_value(
                    GLib.Variant("(s)", (json.dumps(self._commands),))
                )

            elif method == "SaveCommands":
                (json_str,) = params
                self._commands = json.loads(json_str)
                save_commands(self._commands)
                invocation.return_value(GLib.Variant("()", ()))

            elif method == "RunCommand":
                (command_id,) = params
                cmd = self._find_command(command_id)
                if cmd is None:
                    invocation.return_dbus_error(
                        f"{DBUS_IFACE}.Error.NotFound",
                        f"Command {command_id!r} not found",
                    )
                    return
                job_id = str(uuid.uuid4())
                invocation.return_value(GLib.Variant("(s)", (job_id,)))
                GLib.idle_add(self._start_job, job_id, cmd["command"])

            else:
                invocation.return_dbus_error(
                    "org.freedesktop.DBus.Error.UnknownMethod",
                    f"Unknown method: {method}",
                )

        except Exception as exc:
            log.exception("Error in method %s", method)
            invocation.return_dbus_error(f"{DBUS_IFACE}.Error.Internal", str(exc))

    # ── Job execution ─────────────────────────────────────────────────────────

    def _find_command(self, command_id: str) -> dict | None:
        return next((c for c in self._commands if c.get("id") == command_id), None)

    def _start_job(self, job_id: str, command: str):
        def worker():
            ok = False
            try:
                proc = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                self._jobs[job_id] = proc
                for raw in proc.stdout:
                    line = raw.rstrip("\n")
                    GLib.idle_add(self._emit_line, job_id, line)
                proc.wait()
                ok = proc.returncode == 0
            except Exception as exc:
                GLib.idle_add(self._emit_line, job_id, f"[error] {exc}")
            finally:
                self._jobs.pop(job_id, None)
            GLib.idle_add(self._emit_done, job_id, ok)

        threading.Thread(target=worker, daemon=True).start()

    def _emit_line(self, job_id: str, line: str):
        if not self._conn:
            return
        try:
            self._conn.emit_signal(
                None, DBUS_PATH, DBUS_IFACE, "JobLine",
                GLib.Variant("(ss)", (job_id, line)),
            )
        except Exception as exc:
            log.warning("emit JobLine: %s", exc)

    def _emit_done(self, job_id: str, ok: bool):
        if not self._conn:
            return
        try:
            self._conn.emit_signal(
                None, DBUS_PATH, DBUS_IFACE, "JobDone",
                GLib.Variant("(sb)", (job_id, ok)),
            )
        except Exception as exc:
            log.warning("emit JobDone: %s", exc)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    app = CmdPanelDaemon()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
