import json
from typing import Any

import httpx

BASE_URL = "https://www.oma.oomi.fi"


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
