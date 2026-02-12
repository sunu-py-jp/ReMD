"""PyInstaller entry point — launches the Streamlit app and opens the browser."""

import sys
import threading
import time
import webbrowser
from pathlib import Path

import requests


PORT = 8501
URL = f"http://localhost:{PORT}"


def _wait_and_open_browser() -> None:
    """Wait for the Streamlit server to become ready, then open the browser."""
    for _ in range(30):  # up to 30 seconds
        try:
            resp = requests.get(URL, timeout=2)
            if resp.status_code == 200:
                webbrowser.open(URL)
                return
        except Exception:
            pass
        time.sleep(1)


def main() -> None:
    # Ensure the src directory is on the path
    src_dir = Path(__file__).resolve().parent / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # When running from a PyInstaller bundle, _MEIPASS points to the temp dir
    if getattr(sys, "_MEIPASS", None):
        bundle_dir = Path(sys._MEIPASS)
        src_in_bundle = bundle_dir / "src"
        if src_in_bundle.exists() and str(src_in_bundle) not in sys.path:
            sys.path.insert(0, str(src_in_bundle))

    # Force production mode BEFORE bootstrap.run() touches config.
    # In a PyInstaller bundle, streamlit's __file__ no longer contains
    # "site-packages", so it wrongly detects developmentMode=True and
    # rejects server.port.  Pre-loading config with the flag avoids this.
    from streamlit import config as _stconfig

    _stconfig.get_config_options(
        force_reparse=True,
        options_from_flags={"global.developmentMode": False},
    )

    from streamlit.web import bootstrap

    app_path = str(Path(__file__).resolve().parent / "src" / "ReMD" / "app.py")

    # If running from bundle, adjust the path
    if getattr(sys, "_MEIPASS", None):
        app_path = str(Path(sys._MEIPASS) / "src" / "ReMD" / "app.py")

    # Open browser in a background thread once the server is up
    threading.Thread(target=_wait_and_open_browser, daemon=True).start()

    bootstrap.run(
        app_path,
        is_hello=False,
        args=[],
        flag_options={
            "global.developmentMode": False,
            "server.headless": True,
            "server.port": PORT,
            "browser.gatherUsageStats": False,
        },
    )


if __name__ == "__main__":
    main()
