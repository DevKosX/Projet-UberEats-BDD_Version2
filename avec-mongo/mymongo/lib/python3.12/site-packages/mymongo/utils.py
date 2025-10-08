"""Utilities for mymongo."""
import datetime


def utcnow() -> datetime.datetime:
    """Return the current UTC datetime."""
    return datetime.datetime.now(tz=datetime.timezone.utc)
