"""
pyvalidate.schema.schema
~~~~~~~~~~~~~~~~~~~~~~~~~
Schema class: declarative dict validation.
"""
from __future__ import annotations

from typing import Any, Optional

from pyvalidate.schema.field import Field
from pyvalidate.schema.errors import ErrorCollection, FieldError, SchemaError
from pyvalidate.base import ValidationResult


class Schema:
    """Declarative schema for validating dictionaries.

    Usage::

        class UserSchema(Schema):
            email = Field(EmailValidator())
            age   = Field(IntValidator(), RangeValidator(min_value=0, max_value=150))
            name  = Field(LengthValidator(min_length=1, max_length=100))

        result = UserSchema().validate({"email": "a@b.com", "age": 25, "name": "Alice"})
        # result is a dict[str, ValidationResult]

        clean_data = UserSchema().validate_clean(data)
        # raises SchemaError on failure, returns clean coerced values on success
    """

    def __init__(self, *, allow_extra: bool = False, strip_extra: bool = True) -> None:
        self._allow_extra = allow_extra
        self._strip_extra = strip_extra
        self._fields: dict[str, Field] = self._collect_fields()

    def _collect_fields(self) -> dict[str, Field]:
        fields: dict[str, Field] = {}
        for cls in type(self).__mro__:
            for attr, val in vars(cls).items():
                if isinstance(val, Field) and attr not in fields:
                    fields[attr] = val
        return fields

    def validate(self, data: dict) -> dict[str, ValidationResult]:
        """Validate *data* and return a field-keyed dict of ValidationResults."""
        if not isinstance(data, dict):
            raise TypeError(f"Schema.validate expects a dict, got {type(data).__name__}")

        results: dict[str, ValidationResult] = {}

        for name, field in self._fields.items():
            if name not in data:
                if field.required:
                    results[name] = ValidationResult.fail(
                        f"Field '{name}' is required."
                    )
                else:
                    results[name] = ValidationResult.ok(
                        field.get_default() if field.has_default else None
                    )
                continue
            results[name] = field.validate(data[name])

        if not self._allow_extra:
            extra = set(data.keys()) - set(self._fields.keys())
            if extra:
                for key in extra:
                    results[key] = ValidationResult.fail(
                        f"Unexpected field '{key}' is not allowed."
                    )

        return results

    def validate_strict(self, data: dict) -> dict[str, Any]:
        """Validate *data*, raising :class:`SchemaError` on any failure.

        Returns a dict of clean (coerced) values on success.
        """
        results = self.validate(data)
        errors: list[FieldError] = []
        clean: dict[str, Any] = {}

        for name, result in results.items():
            if not result.is_valid:
                errors.append(FieldError(
                    field=name,
                    messages=result.errors,
                    value=result.value,
                ))
            else:
                clean[name] = result.value

        if errors:
            raise SchemaError(errors)
        return clean

    def validate_clean(self, data: dict) -> dict[str, Any]:
        """Alias for :meth:`validate_strict` — returns clean data or raises."""
        return self.validate_strict(data)

    def is_valid(self, data: dict) -> bool:
        """Return True if all fields pass validation."""
        results = self.validate(data)
        return all(r.is_valid for r in results.values())

    def get_errors(self, data: dict) -> dict[str, list[str]]:
        """Return a {field: [error messages]} mapping for invalid fields."""
        results = self.validate(data)
        return {
            name: result.errors
            for name, result in results.items()
            if not result.is_valid
        }

    @property
    def fields(self) -> dict[str, Field]:
        return dict(self._fields)

    def __repr__(self) -> str:
        fields_str = ", ".join(self._fields.keys())
        return f"{type(self).__name__}(fields=[{fields_str}])"


class DynamicSchema(Schema):
    """A schema whose fields are provided at construction time rather than
    as class attributes — useful for schema generation from external configs.

    Usage::

        schema = DynamicSchema(fields={
            "email": Field(EmailValidator()),
            "age":   Field(IntValidator(), required=False, default=0),
        })
    """

    def __init__(
        self,
        fields: dict[str, Field],
        *,
        allow_extra: bool = False,
        strip_extra: bool = True,
    ) -> None:
        self._dynamic_fields = fields
        super().__init__(allow_extra=allow_extra, strip_extra=strip_extra)

    def _collect_fields(self) -> dict[str, Field]:
        base = super()._collect_fields()
        base.update(getattr(self, "_dynamic_fields", {}))
        return base
