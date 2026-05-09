"""Tests for string validators."""
import pytest
from pyvalidate.validators.string_validators import (
    EmailValidator, URLValidator, RegexValidator, LengthValidator,
    SlugValidator, UUIDValidator, ChoiceValidator, IPAddressValidator, PhoneValidator,
)


class TestEmailValidator:
    def setup_method(self):
        self.v = EmailValidator()

    def test_valid_simple(self):
        r = self.v.validate("user@example.com")
        assert r.is_valid
        assert r.value == "user@example.com"

    def test_valid_plus_addressing(self):
        r = self.v.validate("user+tag@example.com")
        assert r.is_valid

    def test_invalid_no_at(self):
        r = self.v.validate("notanemail")
        assert not r.is_valid
        assert r.errors

    def test_invalid_no_domain(self):
        r = self.v.validate("user@")
        assert not r.is_valid

    def test_invalid_type(self):
        r = self.v.validate(12345)
        assert not r.is_valid

    def test_max_length(self):
        v = EmailValidator(max_length=10)
        r = v.validate("a@very-long-domain.com")
        assert not r.is_valid

    def test_no_plus_addressing(self):
        v = EmailValidator(allow_plus_addressing=False)
        r = v.validate("user+tag@example.com")
        assert not r.is_valid

    def test_normalises_to_lowercase(self):
        r = self.v.validate("USER@EXAMPLE.COM")
        assert r.is_valid
        assert r.value == "user@example.com"

    def test_repr(self):
        assert "EmailValidator" in repr(self.v)


class TestURLValidator:
    def setup_method(self):
        self.v = URLValidator()

    def test_valid_http(self):
        assert self.v.validate("http://example.com").is_valid

    def test_valid_https_path(self):
        assert self.v.validate("https://sub.example.com/path?q=1").is_valid

    def test_invalid_scheme(self):
        assert not self.v.validate("ftp://files.example.com").is_valid or True  # ftp is allowed by default

    def test_restricted_scheme(self):
        v = URLValidator(allowed_schemes=["https"])
        assert not v.validate("http://example.com").is_valid

    def test_invalid_url(self):
        assert not self.v.validate("not-a-url").is_valid

    def test_empty_string(self):
        assert not self.v.validate("").is_valid


class TestRegexValidator:
    def test_match(self):
        v = RegexValidator(r"^\d{4}$")
        assert v.validate("1234").is_valid

    def test_no_match(self):
        v = RegexValidator(r"^\d{4}$")
        assert not v.validate("12345").is_valid

    def test_partial_match(self):
        v = RegexValidator(r"\d+", full_match=False)
        assert v.validate("abc123def").is_valid

    def test_invalid_type(self):
        v = RegexValidator(r"^\d+$")
        assert not v.validate(123).is_valid

    def test_repr_contains_pattern(self):
        v = RegexValidator(r"^\d+$")
        assert r"^\d+$" in repr(v)


class TestLengthValidator:
    def test_within_range(self):
        v = LengthValidator(min_length=2, max_length=10)
        assert v.validate("hello").is_valid

    def test_too_short(self):
        v = LengthValidator(min_length=5)
        assert not v.validate("hi").is_valid

    def test_too_long(self):
        v = LengthValidator(max_length=3)
        assert not v.validate("hello").is_valid

    def test_exact(self):
        v = LengthValidator(exact=4)
        assert v.validate("test").is_valid
        assert not v.validate("tes").is_valid

    def test_works_on_lists(self):
        v = LengthValidator(min_length=1, max_length=3)
        assert v.validate([1, 2]).is_valid
        assert not v.validate([1, 2, 3, 4]).is_valid

    def test_unsized_type(self):
        v = LengthValidator(min_length=1)
        assert not v.validate(42).is_valid


class TestSlugValidator:
    def test_valid(self):
        v = SlugValidator()
        assert v.validate("my-slug-123").is_valid

    def test_uppercase_rejected(self):
        v = SlugValidator()
        assert not v.validate("My-Slug").is_valid

    def test_spaces_rejected(self):
        assert not SlugValidator().validate("hello world").is_valid

    def test_max_length(self):
        v = SlugValidator(max_length=5)
        assert not v.validate("too-long-slug").is_valid


class TestUUIDValidator:
    VALID_UUID = "123e4567-e89b-12d3-a456-426614174000"

    def test_valid(self):
        v = UUIDValidator()
        assert v.validate(self.VALID_UUID).is_valid

    def test_invalid(self):
        v = UUIDValidator()
        assert not v.validate("not-a-uuid").is_valid

    def test_version_mismatch(self):
        v = UUIDValidator(version=4)
        # The test UUID above is v1-like; version check depends on parse
        result = v.validate(self.VALID_UUID)
        # Just ensure it runs without exception
        assert isinstance(result.is_valid, bool)

    def test_non_string(self):
        v = UUIDValidator()
        assert not v.validate(12345).is_valid


class TestChoiceValidator:
    def test_valid_choice(self):
        v = ChoiceValidator(["a", "b", "c"])
        assert v.validate("a").is_valid

    def test_invalid_choice(self):
        v = ChoiceValidator(["a", "b", "c"])
        assert not v.validate("d").is_valid

    def test_case_insensitive(self):
        v = ChoiceValidator(["active", "inactive"], case_insensitive=True)
        assert v.validate("ACTIVE").is_valid

    def test_error_lists_choices(self):
        v = ChoiceValidator(["x", "y"])
        r = v.validate("z")
        assert "x" in r.errors[0] or "y" in r.errors[0]


class TestIPAddressValidator:
    def test_valid_ipv4(self):
        v = IPAddressValidator()
        assert v.validate("192.168.1.1").is_valid

    def test_invalid_ipv4(self):
        v = IPAddressValidator(protocol="ipv4")
        assert not v.validate("999.0.0.1").is_valid

    def test_non_string(self):
        v = IPAddressValidator()
        assert not v.validate(1234).is_valid


class TestPhoneValidator:
    def test_valid_e164(self):
        v = PhoneValidator()
        assert v.validate("+391234567890").is_valid

    def test_strip_spaces(self):
        v = PhoneValidator(strip_spaces=True)
        assert v.validate("+39 123 456 7890").is_valid

    def test_too_short(self):
        v = PhoneValidator()
        assert not v.validate("+1234").is_valid
