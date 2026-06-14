import sys
import os


def _ensure_gi_typelib_path():
    """
    gi needs GI_TYPELIB_PATH to find typelib files that aren't in the
    default search path. Rather than hardcoding a path, we search common
    locations and add any that exist and aren't already in the variable.
    """
    import glob
    candidates = glob.glob("/usr/lib*/girepository-1.0") + \
                 glob.glob("/usr/local/lib*/girepository-1.0")

    existing = set(
        p for p in os.environ.get("GI_TYPELIB_PATH", "").split(":") if p
    )
    additions = [p for p in candidates if p not in existing and os.path.isdir(p)]

    if additions:
        all_paths = ":".join(list(existing) + additions)
        os.environ["GI_TYPELIB_PATH"] = all_paths


def main():
    _ensure_gi_typelib_path()
    from .app import CmdPanelApp
    app = CmdPanelApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
