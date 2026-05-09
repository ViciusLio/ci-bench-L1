"""
pyvalidate.validators.composite_validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Logical combinators: AllValidator, AnyValidator, NotValidator, ConditionalValidator.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from pyvalidate.base import BaseValidator, ValidationResult


class AllValidator(BaseValidator):
    """Passes only when ALL inner validators pass (AND logic).

    Collects all errors rather than short-circuiting, unless
    ``fail_fast=True`` is set.
    """

    error_code = "all_failed"

    def __init__(
        self,
        *validators: BaseValidator,
        fail_fast: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if not validators:
            raise ValueError("AllValidator requires at least one validator.")
        self._validators = validators
        self._fail_fast = fail_fast

    def validate(self, value: Any) -> ValidationResult:
        errors: list[str] = []
        current_value = value
        for validator in self._validators:
            result = validator.validate(current_value)
            if not result.is_valid:
                errors.extend(result.errors)
                if self._fail_fast:
                    return ValidationResult(is_valid=False, errors=errors, value=value)
            else:
                current_value = result.value
        if errors:
            return ValidationResult(is_valid=False, errors=errors, value=value)
        return ValidationResult.ok(current_value)

    def __repr__(self) -> str:
        validators_str = ", ".join(repr(v) for v in self._validators)
        return f"AllValidator({validators_str})"


class AnyValidator(BaseValidator):
    """Passes when ANY one of the inner validators passes (OR logic).

    Returns the result of the first passing validator.
    If all fail, collects all error messages.
    """

    error_code = "any_failed"

    def __init__(
        self,
        *validators: BaseValidator,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if not validators:
            raise ValueError("AnyValidator requires at least one validator.")
        self._validators = validators

    def validate(self, value: Any) -> ValidationResult:
        all_errors: list[str] = []
        for validator in self._validators:
            result = validator.validate(value)
            if result.is_valid:
                return result
            all_errors.extend(result.errors)
        combined = f"None of the validators passed: {'; '.join(all_errors)}"
        return ValidationResult.fail(
            self._custom_message or combined, value=value
        )

    def __repr__(self) -> str:
        validators_str = ", ".join(repr(v) for v in self._validators)
        return f"AnyValidator({validators_str})"


class NotValidator(BaseValidator):
    """Passes when the inner validator FAILS (NOT logic).

    Useful for blacklisting: e.g., ``NotValidator(ChoiceValidator(['admin']))``
    """

    error_code = "not_matched"

    def __init__(
        self,
        inner: BaseValidator,
        *,
        success_message: str = "Value must not match the inner validator.",
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._inner = inner
        self._success_message = success_message

    def validate(self, value: Any) -> ValidationResult:
        result = self._inner.validate(value)
        if result.is_valid:
            return ValidationResult.fail(
                self._custom_message or self._success_message, value=value
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"NotValidator({self._inner!r})"


class ConditionalValidator(BaseValidator):
    """Applies a validator only when a condition is satisfied.

    Parameters
    ----------
    condition:
        A callable receiving the value and returning bool.
    then_validator:
        Applied when condition is True.
    else_validator:
        Applied when condition is False (optional; passes by default).
    """

    error_code = "conditional_failed"

    def __init__(
        self,
        condition: Callable[[Any], bool],
        then_validator: BaseValidator,
        else_validator: Optional[BaseValidator] = None,
        *,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._condition = condition
        self._then = then_validator
        self._else = else_validator

    def validate(self, value: Any) -> ValidationResult:
        try:
            condition_met = self._condition(value)
        except Exception as exc:
            return ValidationResult.fail(
                f"Condition evaluation raised an error: {exc}", value=value
            )
        if condition_met:
            return self._then.validate(value)
        if self._else is not None:
            return self._else.validate(value)
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return (
            f"ConditionalValidator(then={self._then!r}, else={self._else!r})"
        )


class ChainValidator(BaseValidator):
    """Applies validators in sequence, passing the coerced value forward.

    Differs from :class:`AllValidator` in that each validator receives the
    *coerced* output of the previous one, not the original raw value.
    """

    error_code = "chain_failed"

    def __init__(
        self,
        *validators: BaseValidator,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if not validators:
            raise ValueError("ChainValidator requires at least one validator.")
        self._validators = validators

    def validate(self, value: Any) -> ValidationResult:
        current = value
        for validator in self._validators:
            result = validator.validate(current)
            if not result.is_valid:
                return result
            current = result.value
        return ValidationResult.ok(current)

    def __repr__(self) -> str:
        validators_str = " -> ".join(repr(v) for v in self._validators)
        return f"ChainValidator({validators_str})"


class LazyValidator(BaseValidator):
    """A placeholder validator resolved at validation time.

    Useful for building recursive or self-referential schemas.
    The ``resolver`` callable is called on first use and its result cached.
    """

    error_code = "lazy_failed"

    def __init__(
        self,
        resolver: Callable[[], BaseValidator],
        *,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._resolver = resolver
        self._resolved: Optional[BaseValidator] = None

    def validate(self, value: Any) -> ValidationResult:
        if self._resolved is None:
            self._resolved = self._resolver()
        return self._resolved.validate(value)

    def __repr__(self) -> str:
        if self._resolved:
            return f"LazyValidator(resolved={self._resolved!r})"
        return "LazyValidator(unresolved)"
