from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConsumptionRecord:
    timestamp: datetime
    kwh: float
    spot_eur_mwh: float


class LoginError(Exception):
    pass


class AuraTokenNotFound(Exception):
    pass


class SessionExpiredError(Exception):
    pass
