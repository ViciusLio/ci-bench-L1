"""Tests for converters and normalizers."""
import pytest
from datetime import date, datetime
from pyvalidate.transformers.converters import (
    to_int, to_float, to_bool, to_date, to_list, to_upper, to_lower, strip, truncate,
)
from pyvalidate.transformers.normalizers import (
    normalize_whitespace, normalize_email, normalize_phone, slugify,
    normalize_url, strip_html_tags, truncate_words,
)


class TestConverters:
    def test_to_int_from_int(self):
        val, err = to_int(42)
        assert val == 42 and err is None

    def test_to_int_from_string(self):
        val, err = to_int("100")
        assert val == 100 and err is None

    def test_to_int_from_bool_rejected(self):
        _, err = to_int(True)
        assert err is not None

    def test_to_int_bad_string(self):
        _, err = to_int("abc")
        assert err is not None

    def test_to_float_from_int(self):
        val, err = to_float(3)
        assert val == 3.0 and err is None

    def test_to_float_from_string(self):
        val, err = to_float("2.71")
        assert abs(val - 2.71) < 1e-9

    def test_to_bool_true_strings(self):
        for s in ["true", "True", "1", "yes", "YES", "on", "t", "y"]:
            val, err = to_bool(s)
            assert val is True and err is None, f"Failed for {s!r}"

    def test_to_bool_false_strings(self):
        for s in ["false", "False", "0", "no", "off", "f", "n"]:
            val, err = to_bool(s)
            assert val is False and err is None, f"Failed for {s!r}"

    def test_to_bool_ambiguous_int(self):
        _, err = to_bool(2)
        assert err is not None

    def test_to_date_from_string(self):
        val, err = to_date("2024-01-15")
        assert val == date(2024, 1, 15) and err is None

    def test_to_date_from_date(self):
        d = date(2024, 6, 1)
        val, err = to_date(d)
        assert val == d and err is None

    def test_to_date_from_datetime(self):
        dt = datetime(2024, 6, 1, 12, 0)
        val, err = to_date(dt)
        assert val == date(2024, 6, 1)

    def test_to_list_from_string(self):
        val, err = to_list("a,b,c")
        assert val == ["a", "b", "c"] and err is None

    def test_to_list_from_list(self):
        val, err = to_list([1, 2])
        assert val == [1, 2]

    def test_to_upper(self):
        val, err = to_upper("hello")
        assert val == "HELLO" and err is None

    def test_to_lower(self):
        val, err = to_lower("HELLO")
        assert val == "hello" and err is None

    def test_strip(self):
        val, err = strip("  hello  ")
        assert val == "hello" and err is None

    def test_truncate_no_change(self):
        val, err = truncate("hi", 10)
        assert val == "hi"

    def test_truncate_applies(self):
        val, err = truncate("hello world", 8, suffix="...")
        assert val == "hello..."
        assert len(val) == 8


class TestNormalizers:
    def test_normalize_whitespace(self):
        assert normalize_whitespace("  hello   world  ") == "hello world"

    def test_normalize_email(self):
        assert normalize_email("  USER@EXAMPLE.COM  ") == "user@example.com"

    def test_normalize_phone(self):
        assert normalize_phone("+39 02 1234 5678") == "+390212345678"

    def test_slugify_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_slugify_accented(self):
        slug = slugify("Café au lait")
        assert slug == "cafe-au-lait"

    def test_slugify_max_length(self):
        slug = slugify("a very long slug string", max_length=10)
        assert len(slug) <= 10

    def test_normalize_url_lowercases_scheme(self):
        result = normalize_url("HTTP://Example.COM/Path")
        assert result.startswith("http://example.com")

    def test_strip_html_tags(self):
        result = strip_html_tags("<p>Hello <b>World</b></p>")
        assert result == "Hello World"

    def test_truncate_words(self):
        result = truncate_words("one two three four", 2)
        assert result == "one two..."

    def test_truncate_words_no_change(self):
        result = truncate_words("one two", 5)
        assert result == "one two"
