from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class ConsumptionRecord:
    timestamp: datetime
    kwh: Decimal


@dataclass
class AccountInfo:
    customer_id: str
    gsrn: str
    first_name: str
    last_name: str


class LoginError(Exception):
    pass


class AuraTokenNotFound(Exception):
    pass


class FwuidNotFound(Exception):
    pass


class SessionExpiredError(Exception):
    pass
