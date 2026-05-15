import logging
import re
import urllib.parse
from datetime import datetime

import httpx

from . import fetch as _fetch
from ._aura import BASE_URL
from .config import Settings
from .fetch import SessionExpiredError
from .models import ConsumptionRecord

logger = logging.getLogger(__name__)

_FWUID_RE = re.compile(r"/sfsites/auraFW/javascript/([A-Za-z0-9_\-]+)/aura_prod\.js")


class LoginError(Exception):
    pass


class AuraTokenNotFound(Exception):
    pass


class FwuidNotFound(Exception):
    pass


def form_login(username: str, password: str) -> str:
    """POST to /login form, follow redirect, return sid from frontdoor.jsp URL."""
    with httpx.Client(follow_redirects=False, timeout=30) as client:
        response = client.post(
            f"{BASE_URL}/login",
            data={
                "username": username,
                "un": username,
                "pw": password,
                "startURL": "/s/",
                "lt": "standard",
                "Login": "Log In",
                "useSecure": "true",
                "hasRememberUn": "true",
                "display": "page",
            },
        )

    location = response.headers.get("location", "")
    if "frontdoor.jsp" in location and "sid=" in location:
        parsed = urllib.parse.urlparse(location)
        params = urllib.parse.parse_qs(parsed.query)
        sid_list = params.get("sid")
        if sid_list:
            return sid_list[0]

    raise LoginError(
        f"Login failed — no session redirect (status {response.status_code})"
    )


def establish_session(session_id: str) -> tuple[httpx.Client, str, str]:
    """Return (client, aura_token, fwuid) for use in Aura API calls."""
    client = httpx.Client(follow_redirects=True, timeout=30)

    client.get(f"{BASE_URL}/secur/frontdoor.jsp?sid={session_id}&retURL=/s/")
    home = client.get(f"{BASE_URL}/s/")

    # The Aura CSRF token is the __Host-ERIC_PROD... cookie set by the server.
    aura_token = next(
        (v for k, v in client.cookies.items() if "ERIC" in k),
        None,
    )
    if not aura_token:
        raise AuraTokenNotFound(
            "Could not find ERIC session cookie. "
            "Session may have failed or the site structure changed."
        )

    fwuid_match = _FWUID_RE.search(home.text)
    if not fwuid_match:
        raise FwuidNotFound(
            "Could not find fwuid in aura_prod.js script URL. Page structure may have changed."
        )
    fwuid = fwuid_match.group(1)

    return client, aura_token, fwuid


class OomiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.Client | None = None
        self._aura_token: str | None = None
        self._fwuid: str = ""

    def _authenticate(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        logger.info("Logging in to Oomi as %s", self._settings.username)
        session_id = form_login(self._settings.username, self._settings.password)
        logger.info("Establishing Oomi session")
        self._client, self._aura_token, self._fwuid = establish_session(session_id)

    def _ensure_authenticated(self) -> tuple[httpx.Client, str, str]:
        if self._client is None or self._aura_token is None:
            self._authenticate()
        assert self._client is not None
        assert self._aura_token is not None
        return self._client, self._aura_token, self._fwuid

    def get_consumption(
        self, start: datetime, end: datetime
    ) -> list[ConsumptionRecord]:
        client, token, fwuid = self._ensure_authenticated()
        try:
            return _fetch.fetch_consumption(
                client, token, fwuid, self._settings, start, end
            )
        except SessionExpiredError:
            logger.warning("Session expired — re-authenticating")
            self._authenticate()
            assert self._client is not None
            assert self._aura_token is not None
            return _fetch.fetch_consumption(
                self._client, self._aura_token, self._fwuid, self._settings, start, end
            )
