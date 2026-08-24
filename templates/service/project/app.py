"""Minimal runnable service used by the repository template."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def response_for(path: str) -> tuple[HTTPStatus, dict[str, Any]]:
    """Return the template response for a request path."""
    if path == "/healthz":
        return HTTPStatus.OK, {"status": "ok"}
    if path == "/readyz":
        return HTTPStatus.OK, {"status": "ready"}
    if path == "/":
        return HTTPStatus.OK, {
            "service": os.getenv("SERVICE_NAME", "replace-me"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "status": "running",
        }
    return HTTPStatus.NOT_FOUND, {"error": "not_found"}


class ServiceHandler(BaseHTTPRequestHandler):
    """Serve the template's small JSON interface."""

    server_version = "SaaSServiceTemplate/0.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        status, payload = response_for(self.path)
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        message = format % args
        print(
            json.dumps(
                {
                    "level": "info",
                    "client": self.client_address[0],
                    "message": message,
                },
                separators=(",", ":"),
            ),
            flush=True,
        )


def main() -> None:
    """Run the development HTTP server."""
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ServiceHandler)
    print(
        json.dumps(
            {"level": "info", "message": "service_started", "host": host, "port": port},
            separators=(",", ":"),
        ),
        flush=True,
    )
    server.serve_forever()
