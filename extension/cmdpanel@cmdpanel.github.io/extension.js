/**
 * extension.js — CmdPanel GNOME Shell Extension entry point.
 *
 * Loads the widget and delegates everything to it.
 * Kept minimal so GNOME's extension loader has nothing to trip on.
 */

import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import { CmdPanelWidget } from './widget.js';

export default class CmdPanelExtension extends Extension {
    enable() {
        this._widget = new CmdPanelWidget(this);
        this._widget.open();
    }

    disable() {
        this._widget?.close();
        this._widget = null;
    }
}
