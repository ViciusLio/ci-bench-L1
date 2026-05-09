"""
pyvalidate.base
~~~~~~~~~~~~~~~
Core abstractions: ValidationResult, ValidationError, BaseValidator.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Result & Error types
# ---------------------------------------------------------------------------


@dataclass
class ValidationError(Exception):
    """Raised when validation fails and strict mode is enabled."""

    field_path: str
    message: str
    value: Any = None
    code: str = "validation_error"

    def __str__(self) -> str:
        return f"[{self.field_path}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"ValidationError(field_path={self.field_path!r}, "
            f"message={self.message!r}, code={self.code!r})"
        )

    def to_dict(self) -> dict:
        return {
            "field": self.field_path,
            "message": self.message,
            "code": self.code,
        }


@dataclass
class ValidationResult:
    """The outcome of a single validation call.

    Attributes:
        is_valid: True when the value passed all validators.
        errors:   Human-readable error messages collected during validation.
        value:    The (possibly coerced/normalised) value after validation.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    value: Any = None

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        return (
            f"ValidationResult(is_valid={self.is_valid}, "
            f"errors={self.errors!r})"
        )

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another result into this one (AND semantics)."""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            value=other.value if other.is_valid else self.value,
        )

    @classmethod
    def ok(cls, value: Any = None) -> "ValidationResult":
        return cls(is_valid=True, value=value)

    @classmethod
    def fail(cls, *errors: str, value: Any = None) -> "ValidationResult":
        return cls(is_valid=False, errors=list(errors), value=value)


# ---------------------------------------------------------------------------
# Base validator
# ---------------------------------------------------------------------------


class BaseValidator(abc.ABC):
    """Abstract base class for all validators.

    Subclasses must implement :meth:`validate`.
    They may optionally override :meth:`__repr__` and :meth:`description`.
    """

    #: Short machine-readable code used in error messages.
    error_code: str = "invalid"

    def __init__(self, *, message: Optional[str] = None) -> None:
        self._custom_message = message

    @abc.abstractmethod
    def validate(self, value: Any) -> ValidationResult:
        """Validate *value* and return a :class:`ValidationResult`."""

    def __call__(self, value: Any) -> ValidationResult:
        return self.validate(value)

    def __repr__(self) -> str:
        cls = type(self).__name__
        if self._custom_message:
            return f"{cls}(message={self._custom_message!r})"
        return f"{cls}()"

    @property
    def description(self) -> str:
        """Human-readable description of what this validator checks."""
        return type(self).__doc__ or type(self).__name__

    def _make_error(self, default_msg: str, value: Any = None) -> ValidationResult:
        msg = self._custom_message or default_msg
        return ValidationResult.fail(msg, value=value)

    def __and__(self, other: "BaseValidator") -> "AllValidator":
        from pyvalidate.validators.composite_validators import AllValidator
        return AllValidator(self, other)

    def __or__(self, other: "BaseValidator") -> "AnyValidator":
        from pyvalidate.validators.composite_validators import AnyValidator
        return AnyValidator(self, other)

    def __invert__(self) -> "NotValidator":
        from pyvalidate.validators.composite_validators import NotValidator
        return NotValidator(self)


# ---------------------------------------------------------------------------
# Null / required helpers
# ---------------------------------------------------------------------------


class RequiredValidator(BaseValidator):
    """Ensures a value is not None and not an empty string."""

    error_code = "required"

    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            return self._make_error("This field is required.", value=value)
        if isinstance(value, str) and value.strip() == "":
            return self._make_error("This field may not be blank.", value=value)
        return ValidationResult.ok(value)


class OptionalValidator(BaseValidator):
    """Passes None/empty through; delegates to an inner validator otherwise."""

    error_code = "optional"

    def __init__(self, inner: BaseValidator, *, message: Optional[str] = None) -> None:
        super().__init__(message=message)
        self._inner = inner

    def validate(self, value: Any) -> ValidationResult:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return ValidationResult.ok(value)
        return self._inner.validate(value)

    def __repr__(self) -> str:
        return f"OptionalValidator({self._inner!r})"


class NullableValidator(BaseValidator):
    """Allows None explicitly; applies inner validator to non-None values."""

    error_code = "nullable"

    def __init__(self, inner: BaseValidator, *, message: Optional[str] = None) -> None:
        super().__init__(message=message)
        self._inner = inner

    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            return ValidationResult.ok(None)
        return self._inner.validate(value)

    def __repr__(self) -> str:
        return f"NullableValidator({self._inner!r})"
