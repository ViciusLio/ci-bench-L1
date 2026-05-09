"""
pyvalidate.validators.collection_validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validators for collections: list, dict, set, tuple, and non-empty checks.
"""
from __future__ import annotations

from typing import Any, Optional, Type

from pyvalidate.base import BaseValidator, ValidationResult


class ListValidator(BaseValidator):
    """Validates that a value is a list, optionally checking each item.

    Parameters
    ----------
    item_validator:
        If provided, every element of the list is validated with this validator.
    min_items / max_items:
        Enforce list length bounds.
    unique:
        If True, duplicate items are rejected.
    """

    error_code = "invalid_list"

    def __init__(
        self,
        *,
        item_validator: Optional[BaseValidator] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._item_validator = item_validator
        self._min = min_items
        self._max = max_items
        self._unique = unique

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, list):
            return self._make_error(
                f"Expected a list, got {type(value).__name__}.", value=value
            )
        if self._min is not None and len(value) < self._min:
            return self._make_error(
                f"List must contain at least {self._min} item(s).", value=value
            )
        if self._max is not None and len(value) > self._max:
            return self._make_error(
                f"List must contain at most {self._max} item(s).", value=value
            )
        if self._unique and len(value) != len(set(map(str, value))):
            return self._make_error(
                "List items must be unique.", value=value
            )
        if self._item_validator:
            errors: list[str] = []
            coerced: list = []
            for i, item in enumerate(value):
                result = self._item_validator.validate(item)
                if not result.is_valid:
                    errors.extend(f"[{i}] {e}" for e in result.errors)
                else:
                    coerced.append(result.value)
            if errors:
                return ValidationResult(is_valid=False, errors=errors, value=value)
            return ValidationResult.ok(coerced)
        return ValidationResult.ok(list(value))

    def __repr__(self) -> str:
        return (
            f"ListValidator(item_validator={self._item_validator!r}, "
            f"min={self._min}, max={self._max}, unique={self._unique})"
        )


class DictValidator(BaseValidator):
    """Validates that a value is a dict, optionally enforcing key/value types.

    Parameters
    ----------
    key_validator:
        Validator applied to every key.
    value_validator:
        Validator applied to every value.
    required_keys:
        A set of keys that must be present.
    forbidden_keys:
        A set of keys that must not be present.
    """

    error_code = "invalid_dict"

    def __init__(
        self,
        *,
        key_validator: Optional[BaseValidator] = None,
        value_validator: Optional[BaseValidator] = None,
        required_keys: Optional[set] = None,
        forbidden_keys: Optional[set] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._key_v = key_validator
        self._val_v = value_validator
        self._required = required_keys or set()
        self._forbidden = forbidden_keys or set()

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, dict):
            return self._make_error(
                f"Expected a dict, got {type(value).__name__}.", value=value
            )
        errors: list[str] = []

        missing = self._required - set(value.keys())
        if missing:
            errors.append(f"Missing required keys: {sorted(missing)}")

        present_forbidden = self._forbidden & set(value.keys())
        if present_forbidden:
            errors.append(f"Forbidden keys present: {sorted(present_forbidden)}")

        if errors:
            return ValidationResult(is_valid=False, errors=errors, value=value)

        coerced: dict = {}
        for k, v in value.items():
            ck = k
            cv = v
            if self._key_v:
                kr = self._key_v.validate(k)
                if not kr.is_valid:
                    errors.extend(f"key {k!r}: {e}" for e in kr.errors)
                else:
                    ck = kr.value
            if self._val_v:
                vr = self._val_v.validate(v)
                if not vr.is_valid:
                    errors.extend(f"[{k!r}] {e}" for e in vr.errors)
                else:
                    cv = vr.value
            coerced[ck] = cv

        if errors:
            return ValidationResult(is_valid=False, errors=errors, value=value)
        return ValidationResult.ok(coerced)

    def __repr__(self) -> str:
        return (
            f"DictValidator(required_keys={self._required!r}, "
            f"forbidden_keys={self._forbidden!r})"
        )


class SetValidator(BaseValidator):
    """Validates that a value is a set or frozenset."""

    error_code = "invalid_set"

    def __init__(
        self,
        *,
        item_validator: Optional[BaseValidator] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._item_validator = item_validator
        self._min = min_items
        self._max = max_items

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (set, frozenset)):
            if isinstance(value, list):
                value = set(value)
            else:
                return self._make_error(
                    f"Expected a set, got {type(value).__name__}.", value=value
                )
        if self._min is not None and len(value) < self._min:
            return self._make_error(
                f"Set must contain at least {self._min} item(s).", value=value
            )
        if self._max is not None and len(value) > self._max:
            return self._make_error(
                f"Set must contain at most {self._max} item(s).", value=value
            )
        if self._item_validator:
            errors: list[str] = []
            coerced: set = set()
            for item in value:
                result = self._item_validator.validate(item)
                if not result.is_valid:
                    errors.extend(f"item {item!r}: {e}" for e in result.errors)
                else:
                    coerced.add(result.value)
            if errors:
                return ValidationResult(is_valid=False, errors=errors, value=value)
            return ValidationResult.ok(coerced)
        return ValidationResult.ok(set(value))

    def __repr__(self) -> str:
        return (
            f"SetValidator(min={self._min}, max={self._max})"
        )


class TupleValidator(BaseValidator):
    """Validates a tuple with a fixed schema (one validator per position)."""

    error_code = "invalid_tuple"

    def __init__(
        self,
        *validators: BaseValidator,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._validators = validators

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (tuple, list)):
            return self._make_error(
                f"Expected a tuple, got {type(value).__name__}.", value=value
            )
        if len(value) != len(self._validators):
            return self._make_error(
                f"Expected {len(self._validators)} elements, got {len(value)}.",
                value=value,
            )
        errors: list[str] = []
        coerced: list = []
        for i, (v, validator) in enumerate(zip(value, self._validators)):
            result = validator.validate(v)
            if not result.is_valid:
                errors.extend(f"[{i}] {e}" for e in result.errors)
            else:
                coerced.append(result.value)
        if errors:
            return ValidationResult(is_valid=False, errors=errors, value=value)
        return ValidationResult.ok(tuple(coerced))

    def __repr__(self) -> str:
        return f"TupleValidator({', '.join(repr(v) for v in self._validators)})"


class NonEmptyValidator(BaseValidator):
    """Validates that a collection (str, list, dict, set, tuple) is not empty."""

    error_code = "empty_collection"

    def validate(self, value: Any) -> ValidationResult:
        if not hasattr(value, "__len__"):
            return self._make_error(
                f"{type(value).__name__} does not support len().", value=value
            )
        if len(value) == 0:
            return self._make_error(
                f"{type(value).__name__} must not be empty.", value=value
            )
        return ValidationResult.ok(value)


class TypeValidator(BaseValidator):
    """Validates that a value is an instance of one or more expected types."""

    error_code = "invalid_type"

    def __init__(
        self,
        *types: Type,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._types = types

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, self._types):
            expected = " or ".join(t.__name__ for t in self._types)
            return self._make_error(
                f"Expected {expected}, got {type(value).__name__}.", value=value
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        types_str = ", ".join(t.__name__ for t in self._types)
        return f"TypeValidator({types_str})"
