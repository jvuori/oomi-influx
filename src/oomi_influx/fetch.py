import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from .config import BASE_URL, Settings
from .models import AccountInfo, ConsumptionRecord, SessionExpiredError


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


def _aura_call(
    client: httpx.Client,
    aura_token: str,
    fwuid: str,
    classname: str,
    method: str,
    params: dict[str, Any] | None = None,
    page_uri: str = "/s/",
) -> Any:
    action_params: dict[str, Any] = {
        "namespace": "",
        "classname": classname,
        "method": method,
        "cacheable": False,
        "isContinuation": False,
    }
    if params is not None:
        action_params["params"] = params
    action: dict[str, Any] = {
        "id": "1;a",
        "descriptor": "aura://ApexActionController/ACTION$execute",
        "callingDescriptor": "UNKNOWN",
        "params": action_params,
    }

    data = {
        "message": json.dumps({"actions": [action]}),
        "aura.context": _aura_context(fwuid),
        "aura.pageURI": page_uri,
        "aura.token": aura_token,
    }
    response = client.post(
        f"{BASE_URL}/s/sfsites/aura?r=1&aura.ApexAction.execute=1",
        data=data,
        timeout=30,
    )
    response.raise_for_status()
    outer = response.json()
    actions = outer.get("actions", [])
    if not actions:
        raise ValueError(f"No actions in Aura response: {outer!r}")
    return actions[0].get("returnValue", {}).get("returnValue")


def fetch_account_info(
    client: httpx.Client,
    aura_token: str,
    fwuid: str,
) -> AccountInfo:
    customer_info = _aura_call(
        client,
        aura_token,
        fwuid,
        classname="oomi_PortalCommonController",
        method="getCustomerInfo",
    )
    customer_id: str = customer_info["SSN"]

    records = _aura_call(
        client,
        aura_token,
        fwuid,
        classname="oomi_BuyingPathController",
        method="callIp",
        params={
            "ipName": "oomi_GetEnerimCustomerData",
            "ipInput": {"queryParams": f"customerIdentification={customer_id}"},
            "ipOptions": {},
        },
    )
    record = records[0]
    gsrn: str = record["agreements"][0]["meteringPoint"]["basicData"]["identification"]

    return AccountInfo(
        customer_id=customer_id,
        gsrn=gsrn,
        first_name=record["givenName"],
        last_name=record["familyName"],
    )


def fetch_consumption(
    client: httpx.Client,
    aura_token: str,
    fwuid: str,
    settings: Settings,
    start: datetime,
    end: datetime,
) -> list[ConsumptionRecord]:
    url = f"{BASE_URL}/s/sfsites/aura?r=1&aura.ApexAction.execute=1"
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
        kwh_raw = row.get("bn01")
        if kwh_raw is None:
            continue
        # str() gives the shortest round-trip repr, so no float rounding leaks into Decimal.
        kwh = Decimal(str(kwh_raw))
        timestamp = datetime.fromisoformat(row["st"])
        records.append(ConsumptionRecord(timestamp=timestamp, kwh=kwh))

    return records
