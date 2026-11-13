from calendar import monthrange
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.models import as_utc, utc_now

STUDY_TIMEZONE = "Asia/Shanghai"


def local_date(value):
    return as_utc(value).astimezone(ZoneInfo(STUDY_TIMEZONE)).date()


def study_today() -> date:
    return local_date(utc_now())


def period_bounds(period: str, today: date, group_start: date) -> tuple[date, date]:
    if period == "day":
        return today, today
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])
    return group_start, today
