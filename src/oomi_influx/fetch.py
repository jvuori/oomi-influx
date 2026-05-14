import json
from datetime import datetime

import httpx

from .config import Settings
from .models import ConsumptionRecord, SessionExpiredError


def _aura_message(settings: Settings, start: datetime, end: datetime) -> str:
    get_request = json.dumps(
        {
            "startTime": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endTime": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "customerIdentification": settings.customer_id,
            "meteringPointEAN": settings.gsrn,
            "period": "PT15M",
            "fetchParams": ["Consumption"],
            "readingTypes": ["BN01"],
        }
    )
    return json.dumps(
        {
            "actions": [
                {
                    "id": "1;a",
                    "descriptor": "aura://ApexActionController/ACTION$execute",
                    "callingDescriptor": "UNKNOWN",
                    "params": {
                        "namespace": "",
                        "classname": "oomi_ConsumptionController",
                        "method": "getConsumption",
                        "params": {"getRequest": get_request},
                        "cacheable": False,
                        "isContinuation": False,
                    },
                }
            ]
        }
    )


def _aura_context(fwuid: str) -> str:
    return json.dumps(
        {
            "mode": "PROD",
            "fwuid": fwuid,
            "app": "siteforce:communityApp",
            "loaded": {},
            "dn": [],
            "globals": {},
            "uad": True,
        }
    )


def fetch_consumption(
    client: httpx.Client,
    aura_token: str,
    fwuid: str,
    settings: Settings,
    start: datetime,
    end: datetime,
) -> list[ConsumptionRecord]:
    url = f"{settings.base_url}/s/sfsites/aura?r=1&aura.ApexAction.execute=1"
    data = {
        "message": _aura_message(settings, start, end),
        "aura.context": _aura_context(fwuid),
        "aura.pageURI": f"/s/consumption?gsrn={settings.gsrn}",
        "aura.token": aura_token,
    }
    response = client.post(url, data=data, timeout=60)

    if response.status_code == 401 or "/s/login" in str(response.url):
        raise SessionExpiredError("Salesforce session has expired")

    response.raise_for_status()

    outer = response.json()
    if outer.get("exceptionEvent") or outer.get("hasErrors"):
        raise SessionExpiredError("Aura response indicates session error")

    actions = outer.get("actions")
    if not actions:
        raise SessionExpiredError(f"Aura response has no actions: {outer!r}")

    outer_rv = actions[0].get("returnValue")
    if not isinstance(outer_rv, dict):
        raise SessionExpiredError(
            f"Unexpected Aura returnValue type {type(outer_rv).__name__!r}: {outer_rv!r}"
        )

    ndjson_text: str = outer_rv.get("returnValue") or ""

    records: list[ConsumptionRecord] = []
    for line in ndjson_text.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        kwh = row.get("bn01")
        if kwh is None:
            continue
        timestamp = datetime.fromisoformat(row["st"])
        records.append(
            ConsumptionRecord(
                timestamp=timestamp,
                kwh=float(kwh),
            )
        )

    return records
