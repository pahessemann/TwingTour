import json
import mimetypes
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.database.db import Database
from backend.models.errors import ApiError
from backend.routes import auth_routes, game_routes
from backend.routes.realtime_routes import handle_websocket


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"


@dataclass
class RequestContext:
    conn: object
    headers: object
    json: dict
    query: str
    path: str


class Router:
    def __init__(self):
        self.routes = {}

    def add(self, method, path, handler):
        self.routes[(method.upper(), path)] = handler

    def dispatch(self, method, path, request):
        handler = self.routes.get((method.upper(), path))
        if not handler:
            raise ApiError(404, "Route inconnue.")
        return handler(request)


def build_router():
    router = Router()
    auth_routes.register(router)
    game_routes.register(router)
    return router


class EuroTwingoHandler(SimpleHTTPRequestHandler):
    router = build_router()
    db = Database()

    def log_message(self, format, *args):
        print("[EuroTwingo]", format % args)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/ws/events":
            handle_websocket(self)
            return
        if parsed.path.startswith("/api/"):
            self._handle_api("GET")
            return
        self._serve_frontend(parsed.path)

    def do_POST(self):
        self._handle_api("POST")

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(400, "JSON invalide.") from exc

    def _handle_api(self, method):
        parsed = urlparse(self.path)
        try:
            with self.db.session() as conn:
                request = RequestContext(
                    conn=conn,
                    headers=self.headers,
                    json=self._read_json() if method != "GET" else {},
                    query=parsed.query,
                    path=parsed.path,
                )
                payload = self.router.dispatch(method, parsed.path, request)
            self._send_json(200, {"ok": True, "data": payload})
        except ApiError as exc:
            self._send_json(exc.status_code, {"ok": False, "error": exc.message, "details": exc.details})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": "Erreur serveur.", "details": {"type": exc.__class__.__name__, "message": str(exc)}})

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_frontend(self, request_path):
        if request_path in ("", "/"):
            path = FRONTEND_ROOT / "index.html"
        else:
            clean = request_path.lstrip("/")
            if clean.startswith("assets/"):
                path = FRONTEND_ROOT / clean
            else:
                path = FRONTEND_ROOT / clean
            if not path.exists() and "." not in Path(clean).name:
                path = FRONTEND_ROOT / "index.html"

        try:
            resolved = path.resolve()
            if FRONTEND_ROOT.resolve() not in resolved.parents and resolved != FRONTEND_ROOT.resolve():
                raise ApiError(403, "Acces refuse.")
            if not resolved.exists() or not resolved.is_file():
                self.send_error(404, "File not found")
                return
            content = resolved.read_bytes()
            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except ApiError as exc:
            self._send_json(exc.status_code, {"ok": False, "error": exc.message})


def run(host="127.0.0.1", port=8010):
    EuroTwingoHandler.db.init()
    server = ThreadingHTTPServer((host, port), EuroTwingoHandler)
    print(f"EuroTwingo roule sur http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Arret EuroTwingo.")
    finally:
        server.server_close()
