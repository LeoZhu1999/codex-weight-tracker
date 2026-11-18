from __future__ import annotations

import json
import mimetypes
import os
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.error import URLError
from urllib.request import Request, urlopen

from .analytics import daily_dashboard
from .config import AppConfig, default_data_dir
from .service import WeightService


STATIC_DIR = Path(__file__).with_name("static")
STATE_FILENAME = "dashboard-state.json"
DEFAULT_IDLE_SECONDS = 120


def _runtime_dir() -> Path:
    path = default_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return _runtime_dir() / STATE_FILENAME


def _read_state() -> dict | None:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _clear_state(token: str | None = None) -> None:
    path = _state_path()
    state = _read_state()
    if token and state and state.get("token") != token:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _existing_dashboard_url() -> str | None:
    state = _read_state()
    if not state or not isinstance(state.get("url"), str) or not isinstance(state.get("token"), str):
        return None
    request = Request(f"{state['url']}api/health", headers={"X-Weight-Tracker-Token": state["token"]})
    try:
        with urlopen(request, timeout=0.5) as response:
            if response.status == HTTPStatus.OK:
                return state["url"]
    except (URLError, OSError, ValueError):
        _clear_state()
    return None


class DashboardServer:
    """Single local dashboard server, shared by MCP and the Windows launcher."""

    _instance: ClassVar["DashboardServer | None"] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, config: AppConfig, idle_seconds: int = DEFAULT_IDLE_SECONDS):
        self.config = config
        self.service = WeightService(config)
        self.token = secrets.token_urlsafe(32)
        self.idle_seconds = idle_seconds
        self.last_heartbeat = time.monotonic()
        self.stopped = threading.Event()
        self._stop_lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _authorized(self) -> bool:
                return secrets.compare_digest(self.headers.get("X-Weight-Tracker-Token", ""), owner.token)

            def _send_bytes(self, status: int, content_type: str, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _serve_asset(self, relative: str) -> None:
                candidate = (STATIC_DIR / relative).resolve()
                try:
                    candidate.relative_to(STATIC_DIR.resolve())
                except ValueError:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                if not candidate.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                    content_type += "; charset=utf-8"
                self._send_bytes(HTTPStatus.OK, content_type, candidate.read_bytes())

            def do_GET(self) -> None:
                path = self.path.split("?", 1)[0]
                if path == "/":
                    html = (STATIC_DIR / "dashboard.html").read_text(encoding="utf-8").replace("__DASHBOARD_TOKEN__", owner.token)
                    self._send_bytes(HTTPStatus.OK, "text/html; charset=utf-8", html.encode("utf-8"))
                    return
                if path.startswith("/assets/"):
                    self._serve_asset(path.removeprefix("/assets/"))
                    return
                if path == "/api/dashboard":
                    try:
                        payload = daily_dashboard(owner.service.list_records(), owner.config.timezone, owner.config.height_cm, owner.config.bmi_standard, owner.config.display_weight_unit)
                        self._send_bytes(HTTPStatus.OK, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                    except Exception as exc:
                        self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
                    return
                if path == "/api/health":
                    if not self._authorized():
                        self.send_error(HTTPStatus.FORBIDDEN)
                        return
                    self._send_bytes(HTTPStatus.OK, "application/json; charset=utf-8", b'{"status":"ok"}')
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                path = self.path.split("?", 1)[0]
                if not self._authorized():
                    self.send_error(HTTPStatus.FORBIDDEN)
                    return
                if path == "/api/heartbeat":
                    owner.last_heartbeat = time.monotonic()
                    self.send_response(HTTPStatus.NO_CONTENT)
                    self.end_headers()
                    return
                if path == "/api/shutdown":
                    self.send_response(HTTPStatus.NO_CONTENT)
                    self.end_headers()
                    threading.Thread(target=owner.stop, daemon=True).start()
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, *_: object) -> None:
                return

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True, name="weight-tracker-dashboard")
        self.thread.start()
        _state_path().write_text(json.dumps({"url": self.url, "token": self.token, "pid": os.getpid()}), encoding="utf-8")
        self.monitor = threading.Thread(target=self._monitor_idle, daemon=True, name="weight-tracker-dashboard-idle")
        self.monitor.start()

    def _monitor_idle(self) -> None:
        interval = min(5, max(0.1, self.idle_seconds / 4))
        while not self.stopped.wait(interval):
            if time.monotonic() - self.last_heartbeat >= self.idle_seconds:
                self.stop()
                return

    @classmethod
    def start_with_ownership(cls, config: AppConfig) -> tuple[str, bool]:
        with cls._instance_lock:
            if cls._instance is not None and not cls._instance.stopped.is_set():
                return cls._instance.url, True
            existing = _existing_dashboard_url()
            if existing:
                return existing, False
            cls._instance = cls(config, idle_seconds=int(os.environ.get("WEIGHT_TRACKER_DASHBOARD_IDLE_SECONDS", DEFAULT_IDLE_SECONDS)))
            return cls._instance.url, True

    @classmethod
    def start(cls, config: AppConfig) -> str:
        return cls.start_with_ownership(config)[0]

    @classmethod
    def wait_for_stop(cls) -> None:
        with cls._instance_lock:
            instance = cls._instance
        if instance is not None:
            instance.wait()

    def wait(self) -> None:
        self.stopped.wait()

    def stop(self) -> None:
        with self._stop_lock:
            if self.stopped.is_set():
                return
            _clear_state(self.token)
            self.httpd.shutdown()
            self.httpd.server_close()
            with self._instance_lock:
                if DashboardServer._instance is self:
                    DashboardServer._instance = None
            self.stopped.set()
