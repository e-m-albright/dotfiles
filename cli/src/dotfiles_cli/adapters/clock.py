"""Real clock implementation of the Clock port."""

from datetime import datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()
