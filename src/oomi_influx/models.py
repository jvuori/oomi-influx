from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class ConsumptionRecord:
    timestamp: datetime
    kwh: Decimal


class LoginError(Exception):
    pass


class AuraTokenNotFound(Exception):
    pass


class SessionExpiredError(Exception):
    pass
