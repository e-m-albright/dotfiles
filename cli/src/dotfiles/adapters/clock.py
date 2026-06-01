"""Real clock implementation of the Clock port."""

from datetime import UTC, datetime


class SystemClock:
    """Returns the current time as a timezone-aware UTC datetime."""

    def now(self) -> datetime:
        return datetime.now(UTC)
