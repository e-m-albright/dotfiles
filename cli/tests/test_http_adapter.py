"""Tests for the HttpClient port, UrllibHttpClient adapter, and FakeHttpClient."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from dotfiles_cli.adapters.http import HttpError, UrllibHttpClient
from dotfiles_cli.core.ports import HttpClient
from tests.fakes import FakeHttpClient

# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_urllib_client_is_http_client() -> None:
    assert isinstance(UrllibHttpClient(), HttpClient)


def test_fake_http_client_is_http_client() -> None:
    assert isinstance(FakeHttpClient(), HttpClient)


# ---------------------------------------------------------------------------
# FakeHttpClient — recording and scripted responses
# ---------------------------------------------------------------------------


def test_fake_get_records_url() -> None:
    fake = FakeHttpClient()
    fake.get_json("http://localhost:1234/api/v0/models")
    assert fake.gets == ["http://localhost:1234/api/v0/models"]


def test_fake_get_returns_scripted_payload() -> None:
    fake = FakeHttpClient()
    payload = {"data": [{"id": "my-model", "state": "loaded"}]}
    fake.script_get("http://localhost:1234/api/v0/models", payload)
    assert fake.get_json("http://localhost:1234/api/v0/models") == payload


def test_fake_get_returns_empty_dict_by_default() -> None:
    fake = FakeHttpClient()
    assert fake.get_json("http://localhost:1234/api/v0/models") == {}


def test_fake_post_records_url_and_body() -> None:
    fake = FakeHttpClient()
    body = {"model": "my-model", "messages": [{"role": "user", "content": "hi"}]}
    fake.post_json("http://localhost:1234/api/v0/chat/completions", body)
    assert fake.posts == [("http://localhost:1234/api/v0/chat/completions", body)]


def test_fake_post_returns_scripted_payload() -> None:
    fake = FakeHttpClient()
    url = "http://localhost:1234/api/v0/chat/completions"
    response = {"choices": [{"message": {"content": "hello"}}], "stats": {}}
    fake.script_post(url, response)
    assert fake.post_json(url, {}) == response


def test_fake_post_returns_empty_dict_by_default() -> None:
    fake = FakeHttpClient()
    assert fake.post_json("http://localhost:1234/api/v0/chat/completions", {}) == {}


# ---------------------------------------------------------------------------
# UrllibHttpClient — GET (monkeypatched)
# ---------------------------------------------------------------------------


def _make_response(payload: dict) -> MagicMock:  # type: ignore[type-arg]
    """Build a context-manager mock that returns JSON bytes."""
    body = json.dumps(payload).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_urllib_get_json_returns_parsed_response() -> None:
    client = UrllibHttpClient()
    payload = {"data": [{"id": "llama-3.2", "state": "loaded"}]}
    with patch("urllib.request.urlopen", return_value=_make_response(payload)):
        result = client.get_json("http://localhost:1234/api/v0/models")
    assert result == payload


def test_urllib_post_json_returns_parsed_response() -> None:
    client = UrllibHttpClient()
    payload = {"choices": [{"message": {"content": "done"}}], "stats": {"tokens_per_second": 55.0}}
    with patch("urllib.request.urlopen", return_value=_make_response(payload)):
        result = client.post_json(
            "http://localhost:1234/api/v0/chat/completions",
            {"model": "llama", "messages": []},
        )
    assert result == payload


def test_urllib_get_raises_http_error_on_4xx() -> None:
    import urllib.error

    client = UrllibHttpClient()
    exc = urllib.error.HTTPError(
        url="http://localhost:1234/api/v0/models",
        code=404,
        msg="Not Found",
        hdrs=MagicMock(),  # type: ignore[arg-type]
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=exc), pytest.raises(HttpError) as info:
        client.get_json("http://localhost:1234/api/v0/models")
    assert info.value.status == 404


def test_urllib_get_raises_http_error_on_connection_failure() -> None:
    import urllib.error

    client = UrllibHttpClient()
    exc = urllib.error.URLError(reason="Connection refused")
    with patch("urllib.request.urlopen", side_effect=exc), pytest.raises(HttpError) as info:
        client.get_json("http://localhost:1234/api/v0/models")
    assert info.value.status is None
