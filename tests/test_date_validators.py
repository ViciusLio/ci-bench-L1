"""Tests for date validators."""
import pytest
from datetime import date, datetime
from pyvalidate.validators.date_validators import (
    DateValidator, DateTimeValidator, AgeValidator, DateRangeValidator,
    FutureDateValidator, PastDateValidator,
)


class TestDateValidator:
    def test_valid_date_object(self):
        v = DateValidator()
        r = v.validate(date(2024, 1, 15))
        assert r.is_valid and r.value == date(2024, 1, 15)

    def test_valid_string_iso(self):
        v = DateValidator()
        r = v.validate("2024-06-01")
        assert r.is_valid

    def test_invalid_string(self):
        v = DateValidator()
        assert not v.validate("not-a-date").is_valid

    def test_min_date(self):
        v = DateValidator(min_date=date(2024, 1, 1))
        assert not v.validate(date(2023, 12, 31)).is_valid

    def test_max_date(self):
        v = DateValidator(max_date=date(2024, 12, 31))
        assert not v.validate(date(2025, 1, 1)).is_valid

    def test_datetime_accepted(self):
        v = DateValidator()
        r = v.validate(datetime(2024, 6, 1, 12, 0))
        assert r.is_valid
        assert isinstance(r.value, date)


class TestDateTimeValidator:
    def test_valid_datetime(self):
        v = DateTimeValidator()
        r = v.validate(datetime(2024, 1, 1, 12, 0))
        assert r.is_valid

    def test_valid_string(self):
        v = DateTimeValidator()
        assert v.validate("2024-01-01T12:00:00").is_valid

    def test_require_timezone_fails(self):
        v = DateTimeValidator(require_timezone=True)
        assert not v.validate(datetime(2024, 1, 1)).is_valid

    def test_invalid_type(self):
        v = DateTimeValidator()
        assert not v.validate("not-a-datetime").is_valid


class TestAgeValidator:
    def test_minimum_age_18(self):
        v = AgeValidator(min_age=18, reference_date=date(2024, 1, 1))
        assert v.validate(date(2005, 1, 1)).is_valid
        assert not v.validate(date(2010, 1, 1)).is_valid

    def test_future_birthdate_rejected(self):
        v = AgeValidator(reference_date=date(2024, 1, 1))
        assert not v.validate(date(2025, 1, 1)).is_valid

    def test_max_age(self):
        v = AgeValidator(max_age=120, reference_date=date(2024, 1, 1))
        assert not v.validate(date(1900, 1, 1)).is_valid


class TestDateRangeValidator:
    def test_valid_range(self):
        v = DateRangeValidator()
        assert v.validate((date(2024, 1, 1), date(2024, 12, 31))).is_valid

    def test_end_before_start(self):
        v = DateRangeValidator()
        assert not v.validate((date(2024, 12, 31), date(2024, 1, 1))).is_valid

    def test_same_day_allowed(self):
        v = DateRangeValidator(allow_same_day=True)
        assert v.validate((date(2024, 6, 1), date(2024, 6, 1))).is_valid

    def test_same_day_not_allowed(self):
        v = DateRangeValidator(allow_same_day=False)
        assert not v.validate((date(2024, 6, 1), date(2024, 6, 1))).is_valid

    def test_max_span(self):
        v = DateRangeValidator(max_span_days=30)
        assert not v.validate((date(2024, 1, 1), date(2024, 3, 1))).is_valid


class TestFutureDateValidator:
    def test_future_date(self):
        v = FutureDateValidator(reference_date=date(2024, 6, 1))
        assert v.validate(date(2024, 6, 2)).is_valid

    def test_past_date_rejected(self):
        v = FutureDateValidator(reference_date=date(2024, 6, 1))
        assert not v.validate(date(2024, 5, 31)).is_valid

    def test_today_rejected_by_default(self):
        v = FutureDateValidator(reference_date=date(2024, 6, 1))
        assert not v.validate(date(2024, 6, 1)).is_valid

    def test_today_allowed(self):
        v = FutureDateValidator(allow_today=True, reference_date=date(2024, 6, 1))
        assert v.validate(date(2024, 6, 1)).is_valid


class TestPastDateValidator:
    def test_past_date(self):
        v = PastDateValidator(reference_date=date(2024, 6, 1))
        assert v.validate(date(2024, 5, 31)).is_valid

    def test_future_rejected(self):
        v = PastDateValidator(reference_date=date(2024, 6, 1))
        assert not v.validate(date(2024, 6, 2)).is_valid
