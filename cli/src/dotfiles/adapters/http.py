"""Stdlib urllib implementation of the HttpClient port."""

import json
import urllib.error
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    """Raised on non-2xx responses or connection failures."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class UrllibHttpClient:
    """HttpClient backed by stdlib urllib — no extra dependencies."""

    def __init__(self, *, timeout: float = 120.0) -> None:
        self._timeout = timeout

    def get_json(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url, method="GET")
        return self._send(req)

    def post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._send(req)

    def _send(self, req: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
                return json.loads(raw)  # type: ignore[no-any-return]
        except urllib.error.HTTPError as exc:
            raise HttpError(
                f"HTTP {exc.code} from {req.full_url}: {exc.reason}",
                status=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            raise HttpError(f"Connection failed to {req.full_url}: {exc.reason}") from exc
