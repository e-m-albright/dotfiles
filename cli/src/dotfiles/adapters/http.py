"""Stdlib urllib implementation of the HttpClient port."""

import json
import urllib.error
import urllib.request
from typing import Any

from pydantic import TypeAdapter, ValidationError

from dotfiles.adapters.ports import HttpError

# HttpError belongs to the port, not the adapter — `dotfiles.adapters.ports` is its
# single public home. It's imported here only to raise it, not to re-export it.
__all__ = ["UrllibHttpClient"]

# The port promises a JSON object; json.loads alone returns Any and can hand back a
# list or scalar. A typed adapter validates the shape (raising on a non-object)
# without laundering that Any through a suppression — and turns a malformed body
# into the same HttpError as every other transport failure.
_JSON_OBJECT = TypeAdapter(dict[str, object])


class UrllibHttpClient:
    """HttpClient backed by stdlib urllib — no extra dependencies."""

    def __init__(self, *, timeout: float = 300.0) -> None:
        # 300s (not 120s): an LM Studio token-generation bench on a very slow
        # local model can exceed two minutes; the original curl had no timeout.
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
        except urllib.error.HTTPError as exc:
            raise HttpError(
                f"HTTP {exc.code} from {req.full_url}: {exc.reason}",
                status=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            raise HttpError(f"Connection failed to {req.full_url}: {exc.reason}") from exc
        try:
            return _JSON_OBJECT.validate_json(raw)
        except ValidationError as exc:
            raise HttpError(f"Expected a JSON object from {req.full_url}") from exc
