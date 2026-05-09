"""
pyvalidate.validators.numeric_validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validators for numeric values: range, integer, float, positive, percentage,
step, precision, and finite-number checks.
"""
from __future__ import annotations

import math
from typing import Any, Optional, Union

from pyvalidate.base import BaseValidator, ValidationResult

Number = Union[int, float]


# ---------------------------------------------------------------------------
# TypeValidator helpers
# ---------------------------------------------------------------------------


class IntValidator(BaseValidator):
    """Validates that a value is an integer (or coercible to one).

    Does not accept booleans unless ``allow_bool=True`` is set, since
    ``isinstance(True, int)`` is True in Python.
    """

    error_code = "invalid_int"

    def __init__(
        self,
        *,
        coerce: bool = False,
        allow_bool: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._coerce = coerce
        self._allow_bool = allow_bool

    def validate(self, value: Any) -> ValidationResult:
        if not self._allow_bool and isinstance(value, bool):
            return self._make_error(
                "Boolean values are not accepted as integers.", value=value
            )
        if isinstance(value, int):
            return ValidationResult.ok(value)
        if self._coerce:
            try:
                coerced = int(value)
                return ValidationResult.ok(coerced)
            except (ValueError, TypeError):
                return self._make_error(
                    f"Cannot coerce {value!r} to an integer.", value=value
                )
        return self._make_error(
            f"Expected an integer, got {type(value).__name__}.", value=value
        )

    def __repr__(self) -> str:
        return f"IntValidator(coerce={self._coerce}, allow_bool={self._allow_bool})"


class FloatValidator(BaseValidator):
    """Validates that a value is a float (or coercible to one).

    By default, infinite and NaN values are rejected unless explicitly allowed.
    """

    error_code = "invalid_float"

    def __init__(
        self,
        *,
        coerce: bool = False,
        allow_inf: bool = False,
        allow_nan: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._coerce = coerce
        self._allow_inf = allow_inf
        self._allow_nan = allow_nan

    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, bool):
            return self._make_error(
                "Boolean values are not accepted as floats.", value=value
            )
        if isinstance(value, (int, float)):
            return self._check_special(float(value))
        if self._coerce:
            try:
                coerced = float(value)
                return self._check_special(coerced)
            except (ValueError, TypeError):
                return self._make_error(
                    f"Cannot coerce {value!r} to a float.", value=value
                )
        return self._make_error(
            f"Expected a float, got {type(value).__name__}.", value=value
        )

    def _check_special(self, value: float) -> ValidationResult:
        if not self._allow_nan and math.isnan(value):
            return self._make_error("NaN is not a valid float value.", value=value)
        if not self._allow_inf and math.isinf(value):
            return self._make_error(
                "Infinite values are not allowed.", value=value
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return (
            f"FloatValidator(coerce={self._coerce}, "
            f"allow_inf={self._allow_inf}, allow_nan={self._allow_nan})"
        )


# ---------------------------------------------------------------------------
# RangeValidator
# ---------------------------------------------------------------------------


class RangeValidator(BaseValidator):
    """Validates that a numeric value falls within [min_value, max_value].

    Both bounds are inclusive by default; pass ``exclusive_min=True`` or
    ``exclusive_max=True`` to make them exclusive.
    """

    error_code = "out_of_range"

    def __init__(
        self,
        *,
        min_value: Optional[Number] = None,
        max_value: Optional[Number] = None,
        exclusive_min: bool = False,
        exclusive_max: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._min = min_value
        self._max = max_value
        self._exc_min = exclusive_min
        self._exc_max = exclusive_max

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        if self._min is not None:
            if self._exc_min and value <= self._min:
                return self._make_error(
                    f"Value must be greater than {self._min}.", value=value
                )
            if not self._exc_min and value < self._min:
                return self._make_error(
                    f"Value must be at least {self._min}.", value=value
                )
        if self._max is not None:
            if self._exc_max and value >= self._max:
                return self._make_error(
                    f"Value must be less than {self._max}.", value=value
                )
            if not self._exc_max and value > self._max:
                return self._make_error(
                    f"Value must be at most {self._max}.", value=value
                )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return (
            f"RangeValidator(min={self._min}, max={self._max}, "
            f"exclusive_min={self._exc_min}, exclusive_max={self._exc_max})"
        )


# ---------------------------------------------------------------------------
# PositiveValidator / NegativeValidator / NonZeroValidator
# ---------------------------------------------------------------------------


class PositiveValidator(BaseValidator):
    """Validates that a numeric value is strictly positive (> 0)."""

    error_code = "not_positive"

    def __init__(self, *, allow_zero: bool = False, message: Optional[str] = None) -> None:
        super().__init__(message=message)
        self._allow_zero = allow_zero

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        if self._allow_zero:
            if value < 0:
                return self._make_error(
                    "Value must be non-negative (>= 0).", value=value
                )
        else:
            if value <= 0:
                return self._make_error(
                    "Value must be positive (> 0).", value=value
                )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"PositiveValidator(allow_zero={self._allow_zero})"


class NegativeValidator(BaseValidator):
    """Validates that a numeric value is strictly negative (< 0)."""

    error_code = "not_negative"

    def __init__(self, *, allow_zero: bool = False, message: Optional[str] = None) -> None:
        super().__init__(message=message)
        self._allow_zero = allow_zero

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        if self._allow_zero:
            if value > 0:
                return self._make_error(
                    "Value must be non-positive (<= 0).", value=value
                )
        else:
            if value >= 0:
                return self._make_error(
                    "Value must be negative (< 0).", value=value
                )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"NegativeValidator(allow_zero={self._allow_zero})"


class NonZeroValidator(BaseValidator):
    """Validates that a numeric value is not zero."""

    error_code = "is_zero"

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        if value == 0:
            return self._make_error("Value must not be zero.", value=value)
        return ValidationResult.ok(value)


# ---------------------------------------------------------------------------
# PercentageValidator
# ---------------------------------------------------------------------------


class PercentageValidator(BaseValidator):
    """Validates that a value is a valid percentage in [0.0, 100.0].

    Accepts both integer (0–100) and fractional (0.0–1.0) formats depending
    on the ``scale`` parameter.
    """

    error_code = "invalid_percentage"

    def __init__(
        self,
        *,
        scale: str = "100",
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if scale not in ("100", "1"):
            raise ValueError("scale must be '100' (0-100) or '1' (0.0-1.0)")
        self._scale = scale
        self._max = 100.0 if scale == "100" else 1.0

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        if value < 0 or value > self._max:
            return self._make_error(
                f"Percentage must be between 0 and {self._max}.", value=value
            )
        return ValidationResult.ok(float(value))

    def __repr__(self) -> str:
        return f"PercentageValidator(scale={self._scale!r})"


# ---------------------------------------------------------------------------
# StepValidator
# ---------------------------------------------------------------------------


class StepValidator(BaseValidator):
    """Validates that a value is a multiple of a given step.

    Useful for enforcing granularity, e.g., price must be a multiple of 0.01.
    """

    error_code = "invalid_step"

    def __init__(
        self,
        step: Number,
        *,
        base: Number = 0,
        tolerance: float = 1e-9,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if step <= 0:
            raise ValueError("step must be positive")
        self._step = step
        self._base = base
        self._tol = tolerance

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        offset = (value - self._base) % self._step
        if offset > self._tol and (self._step - offset) > self._tol:
            return self._make_error(
                f"Value must be a multiple of {self._step} (base={self._base}).",
                value=value,
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"StepValidator(step={self._step}, base={self._base})"


# ---------------------------------------------------------------------------
# DecimalPrecisionValidator
# ---------------------------------------------------------------------------


class DecimalPrecisionValidator(BaseValidator):
    """Validates that a float has at most *max_decimal_places* decimal places."""

    error_code = "invalid_precision"

    def __init__(
        self,
        max_decimal_places: int,
        *,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._max_places = max_decimal_places

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return self._make_error(
                f"Expected a number, got {type(value).__name__}.", value=value
            )
        str_val = f"{value:.{self._max_places + 5}f}".rstrip("0")
        if "." in str_val:
            decimals = len(str_val.split(".")[1])
            if decimals > self._max_places:
                return self._make_error(
                    f"Value has {decimals} decimal places; maximum is {self._max_places}.",
                    value=value,
                )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"DecimalPrecisionValidator(max_decimal_places={self._max_places})"
