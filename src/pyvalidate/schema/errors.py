"""
pyvalidate.schema.errors
~~~~~~~~~~~~~~~~~~~~~~~~~
Error types for schema validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FieldError:
    """Validation error for a single field."""
    field: str
    messages: list[str]
    value: Any = None
    code: str = "validation_error"

    def __str__(self) -> str:
        msgs = "; ".join(self.messages)
        return f"{self.field}: {msgs}"

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "messages": self.messages,
            "code": self.code,
        }


class SchemaError(Exception):
    """Raised when :meth:`Schema.validate_strict` encounters any errors."""

    def __init__(self, errors: list[FieldError]) -> None:
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = [f"  {e}" for e in self.errors]
        return "Schema validation failed:\n" + "\n".join(lines)

    def to_dict(self) -> dict:
        return {"errors": [e.to_dict() for e in self.errors]}

    def __repr__(self) -> str:
        return f"SchemaError({len(self.errors)} error(s))"


class ErrorCollection:
    """Mutable container for accumulating FieldErrors during schema validation."""

    def __init__(self) -> None:
        self._errors: list[FieldError] = []

    def add(self, field: str, messages: list[str], value: Any = None, code: str = "validation_error") -> None:
        self._errors.append(FieldError(field=field, messages=messages, value=value, code=code))

    def has_errors(self) -> bool:
        return len(self._errors) > 0

    def to_list(self) -> list[FieldError]:
        return list(self._errors)

    def to_dict(self) -> dict:
        return {e.field: e.messages for e in self._errors}

    def raise_if_errors(self) -> None:
        if self._errors:
            raise SchemaError(self._errors)

    def __len__(self) -> int:
        return len(self._errors)

    def __repr__(self) -> str:
        return f"ErrorCollection({len(self._errors)} error(s))"
