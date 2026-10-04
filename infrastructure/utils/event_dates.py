"""
Helpers for rendering event datetimes in the event's own timezone.

Event datetimes are stored in UTC; anything user-facing (emails, exports)
should be localized with the event's IANA timezone first so dates match
what attendees see on the ground.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones

from django.core.exceptions import ValidationError

DEFAULT_EVENT_TIMEZONE = 'America/New_York'


def validate_iana_timezone(value: str) -> None:
    if value not in available_timezones():
        raise ValidationError(f"'{value}' is not a valid IANA timezone.")


def localize(dt: datetime, tz_name: str) -> datetime:
    return dt.astimezone(ZoneInfo(tz_name))


def format_event_date(dt: datetime, tz_name: str) -> str:
    """e.g. 'January 22, 2026' (avoids platform-specific %-d)."""
    local = localize(dt, tz_name)
    return f"{local:%B} {local.day}, {local.year}"


def format_event_month(dt: datetime, tz_name: str) -> str:
    """e.g. 'January'."""
    return f"{localize(dt, tz_name):%B}"


def default_mentor_window(start: datetime, end: datetime, tz_name: str) -> tuple[datetime, datetime]:
    """
    Mentors start with the event and leave a day early.

    Mirrors getDefaultMentorWindow in the frontend's eventDateUtils.ts, which
    owns this business logic; keep the two in sync.
    """
    # Aware-datetime arithmetic with a shared tzinfo is wall-clock arithmetic,
    # so subtracting a day keeps the local time across DST transitions.
    mentor_end = localize(end, tz_name) - timedelta(days=1)
    return start, mentor_end


def default_judging_window(start: datetime, end: datetime, tz_name: str) -> tuple[datetime, datetime]:
    """
    Judges attend only the last day: from the event's daily start time on the
    final day until the event ends (midnight if the start time is later in the
    day than the end time).

    Mirrors getDefaultJudgingWindow in the frontend's eventDateUtils.ts.
    """
    local_start = localize(start, tz_name)
    local_end = localize(end, tz_name)
    judging_start = local_end.replace(
        hour=local_start.hour,
        minute=local_start.minute,
        second=0,
        microsecond=0,
    )
    if judging_start > local_end:
        judging_start = local_end.replace(hour=0, minute=0, second=0, microsecond=0)
    return judging_start, end


def get_judging_start(event) -> datetime:
    if event.judging_start_date:
        return event.judging_start_date
    return default_judging_window(event.start_date, event.end_date, event.timezone)[0]
