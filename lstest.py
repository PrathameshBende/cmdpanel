import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gtk4LayerShell, Gio
import sys

def on_activate(a):
    win = Gtk.Window(application=a)
    win.set_decorated(False)
    print("before init:", Gtk4LayerShell.is_layer_window(win))
    Gtk4LayerShell.init_for_window(win)
    print("after init:", Gtk4LayerShell.is_layer_window(win))
    Gtk4LayerShell.set_layer(win, Gtk4LayerShell.Layer.BOTTOM)
    Gtk4LayerShell.set_anchor(win, Gtk4LayerShell.Edge.TOP, True)
    Gtk4LayerShell.set_anchor(win, Gtk4LayerShell.Edge.RIGHT, True)
    Gtk4LayerShell.set_margin(win, Gtk4LayerShell.Edge.TOP, 24)
    Gtk4LayerShell.set_margin(win, Gtk4LayerShell.Edge.RIGHT, 24)
    win.set_child(Gtk.Label(label="LAYER SHELL TEST"))
    a.hold()
    win.present()
    print("presented")

app = Gtk.Application(application_id="io.test.ls3", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
app.connect("activate", on_activate)
app.run(sys.argv)
