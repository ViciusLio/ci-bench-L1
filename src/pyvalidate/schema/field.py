"""
pyvalidate.schema.field
~~~~~~~~~~~~~~~~~~~~~~~~
Field descriptor used in Schema definitions.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Optional

from pyvalidate.base import BaseValidator, ValidationResult

_MISSING = object()


class Field:
    """Declares a single field in a :class:`Schema`.

    Parameters
    ----------
    *validators:
        One or more validators applied in sequence.
    required:
        If True (default), the field must be present in the input dict.
    default:
        Default value when field is absent and ``required=False``.
    default_factory:
        Callable producing the default value (takes priority over ``default``).
    label:
        Human-readable label for error messages.
    description:
        Documentation string for API/doc generation.
    """

    def __init__(
        self,
        *validators: BaseValidator,
        required: bool = True,
        default: Any = _MISSING,
        default_factory: Optional[Callable[[], Any]] = None,
        label: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        self._validators = list(validators)
        self.required = required
        self._default = default
        self._default_factory = default_factory
        self.label = label
        self.description = description

        if required and (default is not _MISSING or default_factory is not None):
            raise ValueError(
                "A field cannot be both required=True and have a default value."
            )

    @property
    def has_default(self) -> bool:
        return self._default is not _MISSING or self._default_factory is not None

    def get_default(self) -> Any:
        if self._default_factory is not None:
            return self._default_factory()
        if self._default is not _MISSING:
            return copy.deepcopy(self._default)
        raise RuntimeError("Field has no default value.")

    def validate(self, value: Any) -> ValidationResult:
        """Run all validators in sequence (chain semantics)."""
        current = value
        for validator in self._validators:
            result = validator.validate(current)
            if not result.is_valid:
                return result
            current = result.value
        return ValidationResult.ok(current)

    def add_validator(self, validator: BaseValidator) -> "Field":
        """Append a validator and return self (builder pattern)."""
        self._validators.append(validator)
        return self

    def __repr__(self) -> str:
        validators_str = ", ".join(repr(v) for v in self._validators)
        return (
            f"Field({validators_str}, required={self.required})"
        )
