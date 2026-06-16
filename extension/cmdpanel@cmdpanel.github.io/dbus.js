/**
 * dbus.js — DBus interface definitions and proxy factory.
 *
 * The Python daemon (cmdpaneld) owns the well-known name
 * "io.github.cmdpanel.Daemon" and exposes one object at
 * "/io/github/cmdpanel/Daemon".
 *
 * Uses Gio.DBusProxy.new for async proxy creation (works on GNOME 45-48).
 */

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

export const DBUS_NAME  = 'io.github.cmdpanel.Daemon';
export const DBUS_PATH  = '/io/github/cmdpanel/Daemon';
export const DBUS_IFACE = 'io.github.cmdpanel.Daemon';

// ── XML interface description ─────────────────────────────────────────────────
const IFACE_XML = `
<node>
  <interface name="io.github.cmdpanel.Daemon">

    <!-- Returns JSON string: list of command objects -->
    <method name="GetCommands">
      <arg direction="out" type="s" name="json"/>
    </method>

    <!-- Saves commands; arg is JSON string of full list -->
    <method name="SaveCommands">
      <arg direction="in"  type="s" name="json"/>
    </method>

    <!-- Starts running a command by id. Returns a job_id string. -->
    <method name="RunCommand">
      <arg direction="in"  type="s" name="command_id"/>
      <arg direction="out" type="s" name="job_id"/>
    </method>

    <!-- Emitted for each stdout/stderr line from a running job -->
    <signal name="JobLine">
      <arg type="s" name="job_id"/>
      <arg type="s" name="line"/>
    </signal>

    <!-- Emitted when a job finishes; ok=true means exit code 0 -->
    <signal name="JobDone">
      <arg type="s" name="job_id"/>
      <arg type="b" name="ok"/>
    </signal>

  </interface>
</node>`;

// Parse once at module load time.
const _nodeInfo = Gio.DBusNodeInfo.new_for_xml(IFACE_XML);
const _ifaceInfo = _nodeInfo.lookup_interface(DBUS_IFACE);

/**
 * Create an async DBus proxy for the daemon.
 *
 * @param {function(Gio.DBusProxy|null, Error|null)} callback
 */
export function createProxy(callback) {
    Gio.DBusProxy.new(
        Gio.DBus.session,
        Gio.DBusProxyFlags.NONE,
        _ifaceInfo,
        DBUS_NAME,
        DBUS_PATH,
        DBUS_IFACE,
        null,
        (source, result) => {
            try {
                const proxy = Gio.DBusProxy.new_finish(result);
                callback(proxy, null);
            } catch (e) {
                callback(null, e);
            }
        }
    );
}

/**
 * Call a DBus method and return a Promise resolving with the GLib.Variant result.
 *
 * @param {Gio.DBusProxy} proxy
 * @param {string} method
 * @param {GLib.Variant|null} params
 * @returns {Promise<GLib.Variant>}
 */
export function callMethod(proxy, method, params = null) {
    return new Promise((resolve, reject) => {
        proxy.call(
            method,
            params,
            Gio.DBusCallFlags.NONE,
            -1,
            null,
            (source, result) => {
                try {
                    resolve(proxy.call_finish(result));
                } catch (e) {
                    reject(e);
                }
            }
        );
    });
}
