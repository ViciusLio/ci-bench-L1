"""
pyvalidate.transformers.converters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Type-coercion helpers: to_int, to_float, to_bool, to_date, to_list, etc.
Each converter returns a (converted_value, error_message | None) tuple.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional, Tuple

ConvertResult = Tuple[Any, Optional[str]]

_TRUTHY = {"1", "true", "yes", "on", "t", "y"}
_FALSY = {"0", "false", "no", "off", "f", "n"}

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
_DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]


def to_int(value: Any, *, base: int = 10) -> ConvertResult:
    """Convert *value* to int.

    Handles str, float (truncates), and bool (rejected).
    """
    if isinstance(value, bool):
        return None, "Boolean cannot be converted to int."
    if isinstance(value, int):
        return value, None
    if isinstance(value, float):
        if value != int(value):
            return None, f"Float {value} has a fractional part; cannot safely convert to int."
        return int(value), None
    if isinstance(value, str):
        try:
            return int(value.strip(), base), None
        except ValueError:
            return None, f"Cannot convert {value!r} to int."
    return None, f"Cannot convert {type(value).__name__} to int."


def to_float(value: Any) -> ConvertResult:
    """Convert *value* to float."""
    if isinstance(value, bool):
        return None, "Boolean cannot be converted to float."
    if isinstance(value, (int, float)):
        return float(value), None
    if isinstance(value, str):
        try:
            return float(value.strip()), None
        except ValueError:
            return None, f"Cannot convert {value!r} to float."
    return None, f"Cannot convert {type(value).__name__} to float."


def to_bool(value: Any) -> ConvertResult:
    """Convert *value* to bool.

    Accepts bool, int (0/1), and common string representations.
    """
    if isinstance(value, bool):
        return value, None
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value), None
        return None, f"Integer {value} cannot be unambiguously converted to bool."
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in _TRUTHY:
            return True, None
        if norm in _FALSY:
            return False, None
        return None, f"Cannot interpret {value!r} as boolean."
    return None, f"Cannot convert {type(value).__name__} to bool."


def to_date(value: Any, *, formats: Optional[list[str]] = None) -> ConvertResult:
    """Convert *value* to :class:`datetime.date`.

    Accepts date, datetime (extracts date), or string.
    """
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    if isinstance(value, str):
        fmts = formats or _DATE_FORMATS
        for fmt in fmts:
            try:
                return datetime.strptime(value.strip(), fmt).date(), None
            except ValueError:
                continue
        return None, f"Cannot parse {value!r} as a date."
    return None, f"Cannot convert {type(value).__name__} to date."


def to_datetime(value: Any, *, formats: Optional[list[str]] = None) -> ConvertResult:
    """Convert *value* to :class:`datetime.datetime`."""
    if isinstance(value, datetime):
        return value, None
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day), None
    if isinstance(value, str):
        fmts = formats or _DATETIME_FORMATS
        for fmt in fmts:
            try:
                return datetime.strptime(value.strip(), fmt), None
            except ValueError:
                continue
        return None, f"Cannot parse {value!r} as a datetime."
    return None, f"Cannot convert {type(value).__name__} to datetime."


def to_list(value: Any, *, separator: str = ",") -> ConvertResult:
    """Convert *value* to a list.

    - Already a list/tuple/set → wrapped in list.
    - String → split by *separator*.
    """
    if isinstance(value, list):
        return value, None
    if isinstance(value, (tuple, set, frozenset)):
        return list(value), None
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(separator)]
        return [p for p in parts if p], None
    return None, f"Cannot convert {type(value).__name__} to list."


def to_upper(value: Any) -> ConvertResult:
    """Convert a string to uppercase."""
    if not isinstance(value, str):
        return None, f"Expected str, got {type(value).__name__}."
    return value.upper(), None


def to_lower(value: Any) -> ConvertResult:
    """Convert a string to lowercase."""
    if not isinstance(value, str):
        return None, f"Expected str, got {type(value).__name__}."
    return value.lower(), None


def strip(value: Any, *, chars: Optional[str] = None) -> ConvertResult:
    """Strip leading/trailing whitespace (or *chars*) from a string."""
    if not isinstance(value, str):
        return None, f"Expected str, got {type(value).__name__}."
    return value.strip(chars), None


def to_str(value: Any) -> ConvertResult:
    """Convert any value to its string representation."""
    return str(value), None


def to_set(value: Any) -> ConvertResult:
    """Convert a list/tuple/string to a set."""
    if isinstance(value, (set, frozenset)):
        return set(value), None
    if isinstance(value, (list, tuple)):
        return set(value), None
    if isinstance(value, str):
        result, err = to_list(value)
        if err:
            return None, err
        return set(result), None
    return None, f"Cannot convert {type(value).__name__} to set."


def truncate(value: Any, max_length: int, *, suffix: str = "...") -> ConvertResult:
    """Truncate a string to *max_length*, appending *suffix* if truncated."""
    if not isinstance(value, str):
        return None, f"Expected str, got {type(value).__name__}."
    if len(value) <= max_length:
        return value, None
    cut = max_length - len(suffix)
    if cut < 0:
        return suffix[:max_length], None
    return value[:cut] + suffix, None
