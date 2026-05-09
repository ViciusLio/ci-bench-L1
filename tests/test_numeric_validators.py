"""Tests for numeric validators."""
import math
import pytest
from pyvalidate.validators.numeric_validators import (
    IntValidator, FloatValidator, RangeValidator, PositiveValidator,
    NegativeValidator, NonZeroValidator, PercentageValidator, StepValidator,
    DecimalPrecisionValidator,
)


class TestIntValidator:
    def test_valid_int(self):
        assert IntValidator().validate(42).is_valid

    def test_bool_rejected_by_default(self):
        assert not IntValidator().validate(True).is_valid

    def test_bool_allowed(self):
        assert IntValidator(allow_bool=True).validate(True).is_valid

    def test_coerce_string(self):
        r = IntValidator(coerce=True).validate("123")
        assert r.is_valid and r.value == 123

    def test_coerce_fails(self):
        assert not IntValidator(coerce=True).validate("abc").is_valid

    def test_no_coerce_string(self):
        assert not IntValidator().validate("123").is_valid


class TestFloatValidator:
    def test_valid_float(self):
        assert FloatValidator().validate(3.14).is_valid

    def test_int_accepted(self):
        r = FloatValidator().validate(3)
        assert r.is_valid and r.value == 3.0

    def test_nan_rejected(self):
        assert not FloatValidator().validate(float("nan")).is_valid

    def test_nan_allowed(self):
        assert FloatValidator(allow_nan=True).validate(float("nan")).is_valid

    def test_inf_rejected(self):
        assert not FloatValidator().validate(float("inf")).is_valid

    def test_inf_allowed(self):
        assert FloatValidator(allow_inf=True).validate(float("inf")).is_valid

    def test_bool_rejected(self):
        assert not FloatValidator().validate(True).is_valid

    def test_coerce_string(self):
        r = FloatValidator(coerce=True).validate("3.14")
        assert r.is_valid
        assert abs(r.value - 3.14) < 1e-9


class TestRangeValidator:
    def test_in_range(self):
        v = RangeValidator(min_value=0, max_value=100)
        assert v.validate(50).is_valid

    def test_below_min(self):
        v = RangeValidator(min_value=10)
        assert not v.validate(5).is_valid

    def test_above_max(self):
        v = RangeValidator(max_value=10)
        assert not v.validate(11).is_valid

    def test_exclusive_min(self):
        v = RangeValidator(min_value=0, exclusive_min=True)
        assert not v.validate(0).is_valid
        assert v.validate(0.001).is_valid

    def test_exclusive_max(self):
        v = RangeValidator(max_value=10, exclusive_max=True)
        assert not v.validate(10).is_valid
        assert v.validate(9.99).is_valid

    def test_non_numeric(self):
        v = RangeValidator(min_value=0)
        assert not v.validate("10").is_valid


class TestPositiveValidator:
    def test_positive(self):
        assert PositiveValidator().validate(1).is_valid

    def test_zero_rejected(self):
        assert not PositiveValidator().validate(0).is_valid

    def test_zero_allowed(self):
        assert PositiveValidator(allow_zero=True).validate(0).is_valid

    def test_negative_rejected(self):
        assert not PositiveValidator().validate(-1).is_valid


class TestNegativeValidator:
    def test_negative(self):
        assert NegativeValidator().validate(-5).is_valid

    def test_zero_rejected(self):
        assert not NegativeValidator().validate(0).is_valid

    def test_zero_allowed(self):
        assert NegativeValidator(allow_zero=True).validate(0).is_valid

    def test_positive_rejected(self):
        assert not NegativeValidator().validate(1).is_valid


class TestNonZeroValidator:
    def test_nonzero(self):
        assert NonZeroValidator().validate(5).is_valid
        assert NonZeroValidator().validate(-1).is_valid

    def test_zero_rejected(self):
        assert not NonZeroValidator().validate(0).is_valid


class TestPercentageValidator:
    def test_valid_0_100(self):
        v = PercentageValidator(scale="100")
        assert v.validate(50.0).is_valid
        assert v.validate(0).is_valid
        assert v.validate(100).is_valid

    def test_out_of_range(self):
        v = PercentageValidator(scale="100")
        assert not v.validate(101).is_valid
        assert not v.validate(-1).is_valid

    def test_scale_1(self):
        v = PercentageValidator(scale="1")
        assert v.validate(0.5).is_valid
        assert not v.validate(1.5).is_valid


class TestStepValidator:
    def test_valid_multiple(self):
        v = StepValidator(0.5)
        assert v.validate(1.5).is_valid

    def test_invalid_step(self):
        v = StepValidator(0.5)
        assert not v.validate(1.3).is_valid

    def test_integer_step(self):
        v = StepValidator(5)
        assert v.validate(15).is_valid
        assert not v.validate(13).is_valid


class TestDecimalPrecisionValidator:
    def test_valid_precision(self):
        v = DecimalPrecisionValidator(2)
        assert v.validate(3.14).is_valid
        assert v.validate(3.1).is_valid
        assert v.validate(3.0).is_valid

    def test_too_many_decimals(self):
        v = DecimalPrecisionValidator(2)
        assert not v.validate(3.141).is_valid

    def test_integer_always_valid(self):
        v = DecimalPrecisionValidator(0)
        assert v.validate(5).is_valid
