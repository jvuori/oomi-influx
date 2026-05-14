import pytest
import httpx
from pytest_httpx import HTTPXMock
from unittest.mock import patch

from oomi_influx.auth import (
    establish_session,
    form_login,
    load_credentials,
    store_credentials,
)
from oomi_influx.models import AuraTokenNotFound, CredentialsNotFound, LoginError

BASE = "https://oomi.test"

HOME_HTML_WITH_ERIC = """
<html><head>
<script src="/s/sfsites/auraFW/javascript/TESTFWUID123/aura_prod.js"></script>
</head><body></body></html>"""

HOME_HTML_NO_ERIC = "<html><body>no ERIC cookie set</body></html>"


def test_form_login_success(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/login",
        status_code=302,
        headers={"location": f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/"},
    )
    assert form_login("user@example.com", "pw", BASE) == "SESSION123"


def test_form_login_bad_credentials(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/login",
        status_code=200,
        text="Please enter your username.",
    )
    with pytest.raises(LoginError, match="Login failed"):
        form_login("user@example.com", "wrong", BASE)


def test_establish_session_extracts_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/",
        status_code=302,
        headers={
            "location": f"{BASE}/s/",
            "set-cookie": "__Host-ERIC_PROD123=eyJhbGc.eyJleHA.SIG; Path=/; Secure",
        },
    )
    httpx_mock.add_response(
        url=f"{BASE}/s/",
        text=HOME_HTML_WITH_ERIC,
    )
    # Second GET to /s/ after redirect
    httpx_mock.add_response(
        url=f"{BASE}/s/",
        text=HOME_HTML_WITH_ERIC,
    )
    client, token, fwuid = establish_session("SESSION123", BASE)
    assert token == "eyJhbGc.eyJleHA.SIG"
    assert fwuid == "TESTFWUID123"
    assert isinstance(client, httpx.Client)


def test_establish_session_no_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/",
        status_code=302,
        headers={"location": f"{BASE}/s/"},
    )
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_ERIC)
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_ERIC)
    with pytest.raises(AuraTokenNotFound):
        establish_session("SESSION123", BASE)


def test_load_credentials_missing() -> None:
    with patch("keyring.get_password", return_value=None):
        with pytest.raises(CredentialsNotFound, match="OOMI_USERNAME"):
            load_credentials()


def test_load_credentials_env_var_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_USERNAME", "env@example.com")
    monkeypatch.setenv("OOMI_PASSWORD", "envpass")
    with patch("keyring.get_password", return_value=None):
        user, pw = load_credentials()
    assert user == "env@example.com"
    assert pw == "envpass"


def test_load_credentials_keyring_error_falls_back_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OOMI_USERNAME", "env@example.com")
    monkeypatch.setenv("OOMI_PASSWORD", "envpass")
    with patch("keyring.get_password", side_effect=Exception("no backend")):
        user, pw = load_credentials()
    assert user == "env@example.com"
    assert pw == "envpass"


def test_store_and_load_credentials() -> None:
    store: dict[tuple[str, str], str] = {}

    def mock_set(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    def mock_get(service: str, username: str) -> str | None:
        return store.get((service, username))

    with (
        patch("keyring.set_password", side_effect=mock_set),
        patch("keyring.get_password", side_effect=mock_get),
    ):
        store_credentials("u@x.com", "secret")
        user, pw = load_credentials()

    assert user == "u@x.com"
    assert pw == "secret"
