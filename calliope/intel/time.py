from datetime import datetime, date
from typing import Union

import tzlocal
from zoneinfo import ZoneInfo


def get_local_datetime(tz: str) -> datetime:
    """
    Gets the current local datetime in the given timezone.
    """
    if not tz:
        tz = tzlocal.get_localzone_name()
    return datetime.now(tz=ZoneInfo(tz))


_LEAP_YEAR = 2000  # dummy leap year to allow input X-02-29 (leap day)


seasons = [
    ('winter', (date(_LEAP_YEAR, 1, 1), date(_LEAP_YEAR, 3, 20))),
    ('spring', (date(_LEAP_YEAR, 3, 21), date(_LEAP_YEAR, 6, 20))),
    ('summer', (date(_LEAP_YEAR, 6, 21), date(_LEAP_YEAR, 9, 22))),
    ('autumn', (date(_LEAP_YEAR, 9, 23), date(_LEAP_YEAR, 12, 20))),
    ('winter', (date(_LEAP_YEAR, 12, 21), date(_LEAP_YEAR, 12, 31)))
]


def get_season(now: Union[datetime, date]) -> str:
    """
    Gets the season in effect at a given datetime or date.
    """
    if isinstance(now, datetime):
        now = now.date()
    now = now.replace(year=_LEAP_YEAR)
    return next(
        season for season, (start, end) in seasons
        if start <= now <= end
    )
