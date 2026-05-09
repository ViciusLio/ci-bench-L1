"""
pyvalidate.validators.date_validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validators for date and datetime values.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any, Optional, Union

from pyvalidate.base import BaseValidator, ValidationResult

DateLike = Union[date, datetime, str]

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
]

_DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]


def _parse_date(value: str) -> Optional[date]:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_datetime(value: str) -> Optional[datetime]:
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# DateValidator
# ---------------------------------------------------------------------------


class DateValidator(BaseValidator):
    """Validates and optionally parses date values.

    Accepts :class:`datetime.date` objects or strings in common formats.
    """

    error_code = "invalid_date"

    def __init__(
        self,
        *,
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        formats: Optional[list[str]] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._min = min_date
        self._max = max_date
        self._formats = formats

    def validate(self, value: Any) -> ValidationResult:
        parsed: Optional[date] = None

        if isinstance(value, datetime):
            parsed = value.date()
        elif isinstance(value, date):
            parsed = value
        elif isinstance(value, str):
            if self._formats:
                for fmt in self._formats:
                    try:
                        parsed = datetime.strptime(value, fmt).date()
                        break
                    except ValueError:
                        continue
            else:
                parsed = _parse_date(value)
            if parsed is None:
                return self._make_error(
                    f"{value!r} is not a recognised date format.", value=value
                )
        else:
            return self._make_error(
                f"Expected a date or date string, got {type(value).__name__}.",
                value=value,
            )

        if self._min and parsed < self._min:
            return self._make_error(
                f"Date must not be before {self._min.isoformat()}.", value=value
            )
        if self._max and parsed > self._max:
            return self._make_error(
                f"Date must not be after {self._max.isoformat()}.", value=value
            )
        return ValidationResult.ok(parsed)

    def __repr__(self) -> str:
        return f"DateValidator(min={self._min}, max={self._max})"


# ---------------------------------------------------------------------------
# DateTimeValidator
# ---------------------------------------------------------------------------


class DateTimeValidator(BaseValidator):
    """Validates and parses datetime values, with optional timezone enforcement."""

    error_code = "invalid_datetime"

    def __init__(
        self,
        *,
        require_timezone: bool = False,
        min_dt: Optional[datetime] = None,
        max_dt: Optional[datetime] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._require_tz = require_timezone
        self._min = min_dt
        self._max = max_dt

    def validate(self, value: Any) -> ValidationResult:
        parsed: Optional[datetime] = None

        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            parsed = datetime(value.year, value.month, value.day)
        elif isinstance(value, str):
            parsed = _parse_datetime(value)
            if parsed is None:
                return self._make_error(
                    f"{value!r} is not a recognised datetime format.", value=value
                )
        else:
            return self._make_error(
                f"Expected a datetime or datetime string, got {type(value).__name__}.",
                value=value,
            )

        if self._require_tz and parsed.tzinfo is None:
            return self._make_error(
                "Datetime must include timezone information.", value=value
            )

        if self._min:
            cmp = parsed.replace(tzinfo=None) if self._min.tzinfo is None else parsed
            if cmp < self._min:
                return self._make_error(
                    f"Datetime must not be before {self._min.isoformat()}.", value=value
                )
        if self._max:
            cmp = parsed.replace(tzinfo=None) if self._max.tzinfo is None else parsed
            if cmp > self._max:
                return self._make_error(
                    f"Datetime must not be after {self._max.isoformat()}.", value=value
                )
        return ValidationResult.ok(parsed)

    def __repr__(self) -> str:
        return (
            f"DateTimeValidator(require_timezone={self._require_tz}, "
            f"min={self._min}, max={self._max})"
        )


# ---------------------------------------------------------------------------
# AgeValidator
# ---------------------------------------------------------------------------


class AgeValidator(BaseValidator):
    """Derives age from a birthdate and validates the result falls in a range.

    Useful for validating "must be at least 18" type constraints directly
    from a date of birth field.
    """

    error_code = "invalid_age"

    def __init__(
        self,
        *,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        reference_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._min_age = min_age
        self._max_age = max_age
        self._ref = reference_date

    def _compute_age(self, birthdate: date, today: date) -> int:
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        return age

    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, datetime):
            birthdate = value.date()
        elif isinstance(value, date):
            birthdate = value
        elif isinstance(value, str):
            birthdate = _parse_date(value)
            if birthdate is None:
                return self._make_error(
                    f"{value!r} is not a recognised date format.", value=value
                )
        else:
            return self._make_error(
                f"Expected a date, got {type(value).__name__}.", value=value
            )

        today = self._ref or date.today()
        if birthdate > today:
            return self._make_error("Birthdate cannot be in the future.", value=value)

        age = self._compute_age(birthdate, today)

        if self._min_age is not None and age < self._min_age:
            return self._make_error(
                f"Age {age} is below minimum required age {self._min_age}.", value=value
            )
        if self._max_age is not None and age > self._max_age:
            return self._make_error(
                f"Age {age} exceeds maximum allowed age {self._max_age}.", value=value
            )
        return ValidationResult.ok(birthdate)

    def __repr__(self) -> str:
        return (
            f"AgeValidator(min_age={self._min_age}, max_age={self._max_age})"
        )


# ---------------------------------------------------------------------------
# DateRangeValidator
# ---------------------------------------------------------------------------


class DateRangeValidator(BaseValidator):
    """Validates a (start_date, end_date) tuple, ensuring ordering and span.

    Accepts a 2-tuple of date/string values. The end date must be >= start date
    (unless ``allow_same_day=False``, in which case it must be strictly after).
    """

    error_code = "invalid_date_range"

    def __init__(
        self,
        *,
        allow_same_day: bool = True,
        max_span_days: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._allow_same = allow_same_day
        self._max_span = max_span_days

    def _coerce(self, val: Any) -> Optional[date]:
        if isinstance(value := val, datetime):
            return value.date()
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            return _parse_date(val)
        return None

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            return self._make_error(
                "Expected a (start_date, end_date) tuple.", value=value
            )
        start_raw, end_raw = value
        start = self._coerce(start_raw)
        end = self._coerce(end_raw)

        if start is None:
            return self._make_error(
                f"Invalid start date: {start_raw!r}.", value=value
            )
        if end is None:
            return self._make_error(
                f"Invalid end date: {end_raw!r}.", value=value
            )

        if self._allow_same:
            if end < start:
                return self._make_error(
                    "End date must not be before start date.", value=value
                )
        else:
            if end <= start:
                return self._make_error(
                    "End date must be strictly after start date.", value=value
                )

        if self._max_span is not None:
            span = (end - start).days
            if span > self._max_span:
                return self._make_error(
                    f"Date range spans {span} days, maximum is {self._max_span}.",
                    value=value,
                )
        return ValidationResult.ok((start, end))

    def __repr__(self) -> str:
        return (
            f"DateRangeValidator(allow_same_day={self._allow_same}, "
            f"max_span_days={self._max_span})"
        )


# ---------------------------------------------------------------------------
# FutureDateValidator / PastDateValidator
# ---------------------------------------------------------------------------


class FutureDateValidator(BaseValidator):
    """Validates that a date is in the future (after today)."""

    error_code = "not_future_date"

    def __init__(
        self,
        *,
        allow_today: bool = False,
        reference_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._allow_today = allow_today
        self._ref = reference_date

    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, datetime):
            parsed = value.date()
        elif isinstance(value, date):
            parsed = value
        elif isinstance(value, str):
            parsed = _parse_date(value)
            if parsed is None:
                return self._make_error(
                    f"{value!r} is not a recognised date format.", value=value
                )
        else:
            return self._make_error(
                f"Expected a date, got {type(value).__name__}.", value=value
            )

        today = self._ref or date.today()
        if self._allow_today:
            if parsed < today:
                return self._make_error(
                    "Date must be today or in the future.", value=value
                )
        else:
            if parsed <= today:
                return self._make_error(
                    "Date must be strictly in the future.", value=value
                )
        return ValidationResult.ok(parsed)

    def __repr__(self) -> str:
        return f"FutureDateValidator(allow_today={self._allow_today})"


class PastDateValidator(BaseValidator):
    """Validates that a date is in the past (before today)."""

    error_code = "not_past_date"

    def __init__(
        self,
        *,
        allow_today: bool = False,
        reference_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._allow_today = allow_today
        self._ref = reference_date

    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, datetime):
            parsed = value.date()
        elif isinstance(value, date):
            parsed = value
        elif isinstance(value, str):
            parsed = _parse_date(value)
            if parsed is None:
                return self._make_error(
                    f"{value!r} is not a recognised date format.", value=value
                )
        else:
            return self._make_error(
                f"Expected a date, got {type(value).__name__}.", value=value
            )

        today = self._ref or date.today()
        if self._allow_today:
            if parsed > today:
                return self._make_error(
                    "Date must be today or in the past.", value=value
                )
        else:
            if parsed >= today:
                return self._make_error(
                    "Date must be strictly in the past.", value=value
                )
        return ValidationResult.ok(parsed)

    def __repr__(self) -> str:
        return f"PastDateValidator(allow_today={self._allow_today})"
