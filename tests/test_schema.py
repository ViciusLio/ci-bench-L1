"""Tests for Schema and Field."""
import pytest
from pyvalidate.schema.schema import Schema, DynamicSchema
from pyvalidate.schema.field import Field
from pyvalidate.schema.errors import SchemaError
from pyvalidate.validators.string_validators import EmailValidator, LengthValidator
from pyvalidate.validators.numeric_validators import IntValidator, RangeValidator


class UserSchema(Schema):
    email = Field(EmailValidator())
    age = Field(IntValidator(coerce=True), RangeValidator(min_value=0, max_value=150))
    name = Field(LengthValidator(min_length=1, max_length=100), required=False, default="Anonymous")


class TestSchema:
    def test_valid_data(self):
        schema = UserSchema()
        results = schema.validate({
            "email": "user@example.com",
            "age": 30,
            "name": "Alice",
        })
        assert all(r.is_valid for r in results.values())

    def test_missing_required_field(self):
        schema = UserSchema()
        results = schema.validate({"age": 25})
        assert not results["email"].is_valid

    def test_default_value_applied(self):
        schema = UserSchema()
        results = schema.validate({"email": "a@b.com", "age": 20})
        assert results["name"].is_valid
        assert results["name"].value == "Anonymous"

    def test_strict_raises_on_error(self):
        schema = UserSchema()
        with pytest.raises(SchemaError) as exc_info:
            schema.validate_strict({"email": "bad-email", "age": 25})
        assert exc_info.value.errors

    def test_strict_returns_clean_data(self):
        schema = UserSchema()
        clean = schema.validate_strict({
            "email": "user@example.com",
            "age": "30",  # coerced
            "name": "Bob",
        })
        assert clean["age"] == 30
        assert clean["email"] == "user@example.com"

    def test_extra_fields_rejected(self):
        schema = UserSchema()
        results = schema.validate({
            "email": "a@b.com",
            "age": 20,
            "unknown_field": "value",
        })
        assert not results["unknown_field"].is_valid

    def test_is_valid_false_when_errors(self):
        schema = UserSchema()
        assert not schema.is_valid({"email": "bad", "age": 25})

    def test_get_errors_only_failed(self):
        schema = UserSchema()
        errors = schema.get_errors({"email": "bad", "age": 25})
        assert "email" in errors
        assert "age" not in errors

    def test_repr(self):
        assert "UserSchema" in repr(UserSchema())


class TestDynamicSchema:
    def test_dynamic_fields(self):
        schema = DynamicSchema(fields={
            "code": Field(LengthValidator(exact=4)),
        })
        assert schema.is_valid({"code": "ABCD"})
        assert not schema.is_valid({"code": "ABC"})

    def test_strict_on_dynamic(self):
        schema = DynamicSchema(fields={
            "n": Field(IntValidator()),
        })
        with pytest.raises(SchemaError):
            schema.validate_strict({"n": "not-an-int"})
