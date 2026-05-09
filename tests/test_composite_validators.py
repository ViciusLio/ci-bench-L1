"""Tests for composite and collection validators."""
import pytest
from pyvalidate.validators.composite_validators import (
    AllValidator, AnyValidator, NotValidator, ConditionalValidator,
    ChainValidator, LazyValidator,
)
from pyvalidate.validators.collection_validators import (
    ListValidator, DictValidator, SetValidator, TupleValidator, NonEmptyValidator, TypeValidator,
)
from pyvalidate.validators.string_validators import EmailValidator, LengthValidator, ChoiceValidator
from pyvalidate.validators.numeric_validators import IntValidator, RangeValidator, PositiveValidator


class TestAllValidator:
    def test_all_pass(self):
        v = AllValidator(IntValidator(coerce=True), RangeValidator(min_value=0, max_value=100))
        r = v.validate("50")
        assert r.is_valid and r.value == 50

    def test_first_fails(self):
        v = AllValidator(IntValidator(), RangeValidator(min_value=0))
        r = v.validate("not-int")
        assert not r.is_valid

    def test_second_fails(self):
        v = AllValidator(IntValidator(), RangeValidator(min_value=0))
        r = v.validate(-5)
        assert not r.is_valid

    def test_collects_all_errors(self):
        v = AllValidator(
            LengthValidator(min_length=10),
            EmailValidator(),
            fail_fast=False,
        )
        r = v.validate("x")
        assert not r.is_valid
        assert len(r.errors) >= 1

    def test_fail_fast_stops_early(self):
        v = AllValidator(
            LengthValidator(min_length=10),
            EmailValidator(),
            fail_fast=True,
        )
        r = v.validate("x")
        assert not r.is_valid

    def test_requires_at_least_one_validator(self):
        with pytest.raises(ValueError):
            AllValidator()

    def test_repr(self):
        v = AllValidator(IntValidator())
        assert "AllValidator" in repr(v)

    def test_and_operator(self):
        v = IntValidator() & RangeValidator(min_value=0)
        r = v.validate(5)
        assert r.is_valid

    def test_and_operator_fail(self):
        v = IntValidator() & RangeValidator(min_value=0)
        assert not v.validate(-1).is_valid


class TestAnyValidator:
    def test_first_passes(self):
        v = AnyValidator(EmailValidator(), LengthValidator(min_length=1))
        assert v.validate("user@example.com").is_valid

    def test_second_passes(self):
        v = AnyValidator(IntValidator(), LengthValidator(min_length=1))
        assert v.validate("hello").is_valid

    def test_none_pass(self):
        v = AnyValidator(IntValidator(), RangeValidator(min_value=100))
        r = v.validate("bad")
        assert not r.is_valid
        assert "None of the validators" in r.errors[0] or r.errors

    def test_requires_at_least_one(self):
        with pytest.raises(ValueError):
            AnyValidator()

    def test_or_operator(self):
        v = IntValidator() | LengthValidator(min_length=1)
        assert v.validate("hello").is_valid
        assert v.validate(42).is_valid


class TestNotValidator:
    def test_passes_when_inner_fails(self):
        v = NotValidator(ChoiceValidator(["admin", "root"]))
        assert v.validate("user").is_valid

    def test_fails_when_inner_passes(self):
        v = NotValidator(ChoiceValidator(["admin", "root"]))
        assert not v.validate("admin").is_valid

    def test_custom_message(self):
        v = NotValidator(IntValidator(), success_message="Must not be an integer.")
        r = v.validate(42)
        assert not r.is_valid
        assert "integer" in r.errors[0].lower()

    def test_invert_operator(self):
        v = ~ChoiceValidator(["banned"])
        assert v.validate("ok").is_valid
        assert not v.validate("banned").is_valid


class TestConditionalValidator:
    def test_condition_true_applies_then(self):
        v = ConditionalValidator(
            condition=lambda x: isinstance(x, str) and x.startswith("email:"),
            then_validator=LengthValidator(min_length=8),
        )
        assert v.validate("email:x").is_valid
        assert not v.validate("email:").is_valid

    def test_condition_false_skips(self):
        v = ConditionalValidator(
            condition=lambda x: False,
            then_validator=IntValidator(),
        )
        assert v.validate("anything").is_valid

    def test_else_validator(self):
        v = ConditionalValidator(
            condition=lambda x: x > 0,
            then_validator=RangeValidator(max_value=100),
            else_validator=RangeValidator(min_value=-100),
        )
        assert v.validate(50).is_valid
        assert v.validate(-50).is_valid
        assert not v.validate(200).is_valid

    def test_condition_exception_caught(self):
        v = ConditionalValidator(
            condition=lambda x: x.nonexistent,
            then_validator=IntValidator(),
        )
        r = v.validate("boom")
        assert not r.is_valid


class TestChainValidator:
    def test_pipes_coerced_value(self):
        v = ChainValidator(
            IntValidator(coerce=True),
            RangeValidator(min_value=0, max_value=10),
        )
        r = v.validate("5")
        assert r.is_valid and r.value == 5

    def test_stops_on_first_fail(self):
        v = ChainValidator(
            IntValidator(),
            RangeValidator(min_value=0),
        )
        assert not v.validate("abc").is_valid

    def test_requires_at_least_one(self):
        with pytest.raises(ValueError):
            ChainValidator()


class TestLazyValidator:
    def test_resolves_on_first_call(self):
        resolved = False

        def make_v():
            nonlocal resolved
            resolved = True
            return IntValidator()

        v = LazyValidator(make_v)
        assert not resolved
        r = v.validate(42)
        assert resolved and r.is_valid

    def test_resolver_called_once(self):
        call_count = 0

        def make_v():
            nonlocal call_count
            call_count += 1
            return IntValidator()

        v = LazyValidator(make_v)
        v.validate(1)
        v.validate(2)
        assert call_count == 1


class TestListValidator:
    def test_valid_list(self):
        v = ListValidator()
        assert v.validate([1, 2, 3]).is_valid

    def test_not_a_list(self):
        assert not ListValidator().validate("not-a-list").is_valid

    def test_min_items(self):
        v = ListValidator(min_items=2)
        assert not v.validate([1]).is_valid
        assert v.validate([1, 2]).is_valid

    def test_max_items(self):
        v = ListValidator(max_items=2)
        assert not v.validate([1, 2, 3]).is_valid

    def test_item_validator(self):
        v = ListValidator(item_validator=IntValidator())
        r = v.validate([1, 2, 3])
        assert r.is_valid

    def test_item_validator_fail(self):
        v = ListValidator(item_validator=IntValidator())
        r = v.validate([1, "bad", 3])
        assert not r.is_valid
        assert any("[1]" in e for e in r.errors)

    def test_unique(self):
        v = ListValidator(unique=True)
        assert not v.validate([1, 1, 2]).is_valid
        assert v.validate([1, 2, 3]).is_valid


class TestDictValidator:
    def test_valid_dict(self):
        assert DictValidator().validate({"a": 1}).is_valid

    def test_not_a_dict(self):
        assert not DictValidator().validate("not-a-dict").is_valid

    def test_required_keys(self):
        v = DictValidator(required_keys={"name", "email"})
        assert not v.validate({"name": "Alice"}).is_valid
        assert v.validate({"name": "Alice", "email": "a@b.com"}).is_valid

    def test_forbidden_keys(self):
        v = DictValidator(forbidden_keys={"password"})
        assert not v.validate({"username": "alice", "password": "secret"}).is_valid


class TestSetValidator:
    def test_valid_set(self):
        assert SetValidator().validate({1, 2, 3}).is_valid

    def test_list_coerced(self):
        r = SetValidator().validate([1, 2, 3])
        assert r.is_valid and isinstance(r.value, set)

    def test_min_items(self):
        v = SetValidator(min_items=2)
        assert not v.validate({1}).is_valid


class TestTupleValidator:
    def test_valid_tuple(self):
        v = TupleValidator(IntValidator(), LengthValidator(min_length=1))
        assert v.validate((42, "hello")).is_valid

    def test_wrong_length(self):
        v = TupleValidator(IntValidator(), IntValidator())
        assert not v.validate((1,)).is_valid

    def test_item_fails(self):
        v = TupleValidator(IntValidator(), IntValidator())
        r = v.validate((1, "bad"))
        assert not r.is_valid
        assert any("[1]" in e for e in r.errors)


class TestNonEmptyValidator:
    def test_non_empty_string(self):
        assert NonEmptyValidator().validate("hello").is_valid

    def test_empty_string_rejected(self):
        assert not NonEmptyValidator().validate("").is_valid

    def test_empty_list_rejected(self):
        assert not NonEmptyValidator().validate([]).is_valid

    def test_empty_dict_rejected(self):
        assert not NonEmptyValidator().validate({}).is_valid


class TestTypeValidator:
    def test_correct_type(self):
        assert TypeValidator(str).validate("hello").is_valid
        assert TypeValidator(int).validate(42).is_valid

    def test_wrong_type(self):
        assert not TypeValidator(int).validate("hello").is_valid

    def test_multiple_types(self):
        v = TypeValidator(str, int)
        assert v.validate("hello").is_valid
        assert v.validate(42).is_valid
        assert not v.validate([]).is_valid
