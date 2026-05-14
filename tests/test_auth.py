import pytest
import httpx
from pytest_httpx import HTTPXMock

from oomi_influx.auth import establish_session, form_login
from oomi_influx.models import AuraTokenNotFound, FwuidNotFound, LoginError

BASE = "https://oomi.test"

HOME_HTML_WITH_ERIC = """
<html><head>
<script src="/s/sfsites/auraFW/javascript/TESTFWUID123/aura_prod.js"></script>
</head><body></body></html>"""

HOME_HTML_NO_ERIC = "<html><body>no ERIC cookie set</body></html>"
HOME_HTML_NO_FWUID = "<html><head></head><body>no aura_prod.js script tag</body></html>"


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
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_WITH_ERIC)
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_WITH_ERIC)
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


def test_establish_session_no_fwuid(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/",
        status_code=302,
        headers={
            "location": f"{BASE}/s/",
            "set-cookie": "__Host-ERIC_PROD123=eyJhbGc.eyJleHA.SIG; Path=/; Secure",
        },
    )
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_FWUID)
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_FWUID)
    with pytest.raises(FwuidNotFound):
        establish_session("SESSION123", BASE)
