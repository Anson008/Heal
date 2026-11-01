"""Standalone desktop entry point: FastAPI on localhost inside a native window."""

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from platformdirs import user_log_dir

APP_NAME = "HEALTool"
FROZEN = getattr(sys, "frozen", False)
API_DIR = Path(__file__).resolve().parent.parent
# PyInstaller unpacks bundled data into _MEIPASS; in development the models
# live in api/ and the UI build in ../web/dist.
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", API_DIR))

if not FROZEN:
    sys.path.insert(0, str(API_DIR / "src"))


def _redirect_output() -> None:
    """A windowed build has no console, so stdout/stderr are None."""
    if sys.stdout is not None and sys.stderr is not None:
        return

    log_dir = Path(user_log_dir(APP_NAME, appauthor=False))
    log_dir.mkdir(parents=True, exist_ok=True)
    stream = open(log_dir / "heal-tool.log", "a", buffering=1, encoding="utf-8")
    sys.stdout = sys.stdout or stream
    sys.stderr = sys.stderr or stream


_redirect_output()

# Settings are read when `config` is first imported, so set them before that.
os.environ.setdefault("MODELS_DIR", str(BUNDLE_DIR / "models"))
os.environ["DOWNLOAD_MODELS"] = "false"

import uvicorn  # noqa: E402
import webview  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from service.main import app as api_app  # noqa: E402

DEFAULT_WEB_DIR = BUNDLE_DIR / "web" if FROZEN else API_DIR.parent / "web" / "dist"
WEB_DIR = Path(os.environ.get("WEB_DIST_DIR", DEFAULT_WEB_DIR))


class SpaFiles(StaticFiles):
    """Serve the built UI; unknown paths get index.html for client-side routing."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return FileResponse(WEB_DIR / "index.html")


def build_app() -> FastAPI:
    # The API keeps the /api prefix the web client already uses, so the UI
    # needs no changes to its request paths.
    # Mount does not run a sub-app's lifespan, so reuse it here to load models.
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=api_app.router.lifespan_context,
    )
    # Mount already supplies the /api root path; the service's own setting is
    # for the nginx proxy and would double it.
    api_app.root_path = ""
    app.mount("/api", api_app)
    app.mount("/", SpaFiles(directory=WEB_DIR, html=True), name="web")
    return app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Api:
    """Exposed to the page as window.pywebview.api."""

    def open_external(self, url: str) -> None:
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)


# Sends target=_blank and off-site links to the system browser instead of a
# second webview window.
LINK_HANDLER = """
document.addEventListener('click', (event) => {
  const link = event.target.closest && event.target.closest('a[href]');
  if (!link) return;
  const url = new URL(link.href, location.href);
  if (url.origin !== location.origin) {
    event.preventDefault();
    window.pywebview.api.open_external(url.href);
  }
}, true);
"""


def wait_until_ready(url: str, thread: threading.Thread, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not thread.is_alive():
            raise RuntimeError("The local server stopped unexpectedly.")
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=2):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError("The local server did not start in time.")


def main() -> None:
    if not (WEB_DIR / "index.html").is_file():
        raise SystemExit(f"Web build not found at {WEB_DIR}. Run `npm run build`.")

    port = free_port()
    server = uvicorn.Server(
        uvicorn.Config(build_app(), host="127.0.0.1", port=port, log_config=None)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    wait_until_ready(url, thread)

    # CI runs the packaged app headlessly to prove the bundle starts and loads models.
    if os.environ.get("HEALTOOL_SMOKE_TEST"):
        server.should_exit = True
        thread.join(timeout=5)
        return

    window = webview.create_window(
        "HEAL Tool", url, js_api=Api(), width=1280, height=860, min_size=(900, 600)
    )
    window.events.loaded += lambda: window.evaluate_js(LINK_HANDLER)
    try:
        webview.start()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
