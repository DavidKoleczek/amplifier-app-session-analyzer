"""Time scope parsing and timezone handling.

Handles conversion between user's local timezone and UTC for filtering sessions.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass
class TimeScope:
    """A time range in UTC for filtering sessions."""

    start_utc: datetime
    end_utc: datetime
    timezone: str  # Original timezone for display purposes

    def contains(self, ts: datetime) -> bool:
        """Check if a timestamp falls within this scope."""
        # Ensure ts is timezone-aware in UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo("UTC"))
        return self.start_utc <= ts <= self.end_utc

    def display_range(self) -> str:
        """Return the time range formatted in the original timezone."""
        tz = ZoneInfo(self.timezone)
        start_local = self.start_utc.astimezone(tz)
        end_local = self.end_utc.astimezone(tz)
        return f"{start_local.strftime('%Y/%m/%d %H:%M')} - {end_local.strftime('%Y/%m/%d %H:%M')} ({self.timezone})"


def parse_time_scope(scope_str: str, timezone: str = "America/New_York") -> TimeScope:
    """Parse a time scope string into a UTC time range.

    Args:
        scope_str: One of:
            - "default": Last full week (Monday 00:00:00 to Sunday 23:59:59)
            - "2026/01/12": Single day (00:00:00 to 23:59:59)
            - "2026/01/10 - 2026/01/12": Date range (first day 00:00 to last day 23:59:59)
        timezone: IANA timezone string (default: America/New_York)

    Returns:
        TimeScope with start_utc and end_utc in UTC
    """
    tz = ZoneInfo(timezone)

    if scope_str == "default":
        # Last full week: Monday 00:00:00 to Sunday 23:59:59
        now = datetime.now(tz)
        # Find last Monday (if today is Monday, go back a week)
        days_since_monday = now.weekday()
        if days_since_monday == 0 and now.hour < 12:
            # If it's Monday morning, use the week before last
            days_since_monday = 7
        last_monday = now - timedelta(days=days_since_monday + 7)
        last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=1)

        last_sunday = last_monday + timedelta(days=6)
        last_sunday = last_sunday.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        return TimeScope(
            start_utc=last_monday.astimezone(ZoneInfo("UTC")),
            end_utc=last_sunday.astimezone(ZoneInfo("UTC")),
            timezone=timezone,
        )

    if " - " in scope_str:
        # Date range: "2026/01/10 - 2026/01/12"
        start_str, end_str = scope_str.split(" - ")
        start_date = datetime.strptime(start_str.strip(), "%Y/%m/%d")
        end_date = datetime.strptime(end_str.strip(), "%Y/%m/%d")

        start_local = start_date.replace(
            hour=0, minute=0, second=0, microsecond=1, tzinfo=tz
        )
        end_local = end_date.replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=tz
        )

        return TimeScope(
            start_utc=start_local.astimezone(ZoneInfo("UTC")),
            end_utc=end_local.astimezone(ZoneInfo("UTC")),
            timezone=timezone,
        )

    # Single day: "2026/01/12"
    date = datetime.strptime(scope_str.strip(), "%Y/%m/%d")
    start_local = date.replace(hour=0, minute=0, second=0, microsecond=1, tzinfo=tz)
    end_local = date.replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=tz
    )

    return TimeScope(
        start_utc=start_local.astimezone(ZoneInfo("UTC")),
        end_utc=end_local.astimezone(ZoneInfo("UTC")),
        timezone=timezone,
    )


def parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse an ISO8601 timestamp string to a timezone-aware datetime.

    Handles formats like: 2026-01-07T21:22:38.416156+00:00
    """
    return datetime.fromisoformat(ts_str)
