from datetime import datetime


def headcount_velocity(timestamps: list[datetime]) -> dict[str, float]:
    if len(timestamps) < 2:
        return {"per_month": 0.0}
    sorted_ts = sorted(timestamps)
    months = max((sorted_ts[-1] - sorted_ts[0]).days / 30.0, 1.0)
    return {"per_month": len(timestamps) / months}
