from datetime import datetime, timezone
from dateutil import parser


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return parser.isoparse(value)
