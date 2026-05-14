from datetime import datetime

import httpx

from .auth import establish_session, form_login
from .config import Settings
from .models import ConsumptionRecord, SessionExpiredError


class OomiSession:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.Client | None = None
        self._aura_token: str | None = None
        self._fwuid: str = ""

    def _authenticate(self) -> None:
        session_id = form_login(self._settings.username, self._settings.password)
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
        from .fetch import fetch_consumption

        client, token, fwuid = self._ensure_authenticated()
        try:
            return fetch_consumption(client, token, fwuid, self._settings, start, end)
        except SessionExpiredError:
            self._authenticate()
            assert self._client is not None
            assert self._aura_token is not None
            return fetch_consumption(
                self._client, self._aura_token, self._fwuid, self._settings, start, end
            )
