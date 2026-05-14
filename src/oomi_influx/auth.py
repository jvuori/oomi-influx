import re
import urllib.parse

import httpx

from .models import AuraTokenNotFound, LoginError

# Matches the fwuid embedded in the aura_prod.js script URL on the /s/ page.
_FWUID_RE = re.compile(r"/sfsites/auraFW/javascript/([A-Za-z0-9_\-]+)/aura_prod\.js")


def form_login(username: str, password: str, base_url: str) -> str:
    """POST to /login form, follow redirect, return sid from frontdoor.jsp URL."""
    with httpx.Client(follow_redirects=False, timeout=30) as client:
        response = client.post(
            f"{base_url}/login",
            data={
                "username": username,
                "un": username,  # JS copies username→un before submit
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


def establish_session(session_id: str, base_url: str) -> tuple[httpx.Client, str, str]:
    """Return (client, aura_token, fwuid) for use in Aura API calls."""
    client = httpx.Client(follow_redirects=True, timeout=30)

    client.get(f"{base_url}/secur/frontdoor.jsp?sid={session_id}&retURL=/s/")
    home = client.get(f"{base_url}/s/")

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
    fwuid = fwuid_match.group(1) if fwuid_match else ""

    return client, aura_token, fwuid
