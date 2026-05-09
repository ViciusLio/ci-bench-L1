"""Tests for ValidationCache and helper utilities."""
import pytest
import threading
from pyvalidate.utils.cache import ValidationCache, get_default_cache, cached_validate, cache_result
from pyvalidate.utils.helpers import (
    is_empty, coerce_type, flatten_errors, format_error_path,
    deep_merge, chunk_list, pick, omit,
)
from pyvalidate.base import ValidationResult


class TestValidationCache:
    def setup_method(self):
        self.cache = ValidationCache(max_size=4)

    def test_miss_returns_none(self):
        assert self.cache.get("FakeValidator", "value") is None

    def test_set_and_get(self):
        r = ValidationResult.ok("test")
        self.cache.set("FakeValidator", "value", r)
        retrieved = self.cache.get("FakeValidator", "value")
        assert retrieved is not None
        assert retrieved.is_valid

    def test_different_keys(self):
        r1 = ValidationResult.ok("a")
        r2 = ValidationResult.fail("error")
        self.cache.set("V", "a", r1)
        self.cache.set("V", "b", r2)
        assert self.cache.get("V", "a").is_valid
        assert not self.cache.get("V", "b").is_valid

    def test_lru_eviction(self):
        for i in range(4):
            self.cache.set("V", str(i), ValidationResult.ok(i))
        # Cache is full; adding another should evict the oldest (key "0")
        self.cache.set("V", "4", ValidationResult.ok(4))
        assert self.cache.get("V", "0") is None
        assert self.cache.get("V", "4") is not None

    def test_invalidate_all(self):
        self.cache.set("V", "a", ValidationResult.ok("a"))
        self.cache.set("V", "b", ValidationResult.ok("b"))
        count = self.cache.invalidate()
        assert count == 2
        assert self.cache.size == 0

    def test_invalidate_by_class(self):
        self.cache.set("V1", "x", ValidationResult.ok("x"))
        self.cache.set("V2", "x", ValidationResult.ok("x"))
        self.cache.invalidate("V1")
        assert self.cache.get("V1", "x") is None
        assert self.cache.get("V2", "x") is not None

    def test_hit_rate(self):
        r = ValidationResult.ok("v")
        self.cache.set("V", "k", r)
        self.cache.get("V", "k")  # hit
        self.cache.get("V", "missing")  # miss
        assert self.cache.hit_rate == 0.5

    def test_stats_structure(self):
        stats = self.cache.stats()
        assert "size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

    def test_thread_safety(self):
        errors: list[Exception] = []

        def worker(vid: int):
            try:
                for i in range(50):
                    key = f"val_{i % 5}"
                    r = ValidationResult.ok(key)
                    self.cache.set(f"V{vid}", key, r)
                    self.cache.get(f"V{vid}", key)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"

    def test_repr_contains_stats(self):
        r = repr(self.cache)
        assert "ValidationCache" in r
        assert "0/4" in r

    def test_module_level_helpers(self):
        from pyvalidate.validators.string_validators import EmailValidator
        v = EmailValidator()
        assert cached_validate(v, "test@example.com") is None
        result = v.validate("test@example.com")
        cache_result(v, "test@example.com", result)
        cached = cached_validate(v, "test@example.com")
        assert cached is not None and cached.is_valid


class TestHelpers:
    def test_is_empty_none(self):
        assert is_empty(None)

    def test_is_empty_blank_string(self):
        assert is_empty("   ")

    def test_is_empty_empty_list(self):
        assert is_empty([])

    def test_is_empty_empty_dict(self):
        assert is_empty({})

    def test_is_empty_nonempty(self):
        assert not is_empty("hello")
        assert not is_empty([1])
        assert not is_empty(0)
        assert not is_empty(False)

    def test_coerce_type_already_correct(self):
        result = coerce_type(42, int)
        assert result == 42

    def test_coerce_type_string_to_int(self):
        result = coerce_type("5", int)
        assert result == 5

    def test_coerce_type_fails_returns_none(self):
        result = coerce_type("abc", int)
        assert result is None

    def test_coerce_type_strict_raises(self):
        with pytest.raises(TypeError):
            coerce_type("abc", int, strict=True)

    def test_flatten_errors_simple(self):
        errors = {"email": ["Invalid email"], "age": ["Too young"]}
        flat = flatten_errors(errors)
        assert "email: Invalid email" in flat
        assert "age: Too young" in flat

    def test_flatten_errors_nested(self):
        errors = {"address": {"city": ["Required"], "zip": ["Invalid"]}}
        flat = flatten_errors(errors)
        assert any("address.city" in e for e in flat)
        assert any("address.zip" in e for e in flat)

    def test_format_error_path(self):
        assert format_error_path(["user", "address", "city"]) == "user.address.city"

    def test_format_error_path_single(self):
        assert format_error_path(["name"]) == "name"

    def test_deep_merge_basic(self):
        result = deep_merge({"a": 1, "b": 2}, {"b": 99, "c": 3})
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_deep_merge_nested(self):
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 99, "c": 3}}
        result = deep_merge(base, override)
        assert result["x"] == {"a": 1, "b": 99, "c": 3}

    def test_deep_merge_does_not_mutate(self):
        base = {"a": 1}
        deep_merge(base, {"b": 2})
        assert "b" not in base

    def test_chunk_list_equal_size(self):
        chunks = chunk_list([1, 2, 3, 4], 2)
        assert chunks == [[1, 2], [3, 4]]

    def test_chunk_list_remainder(self):
        chunks = chunk_list([1, 2, 3, 4, 5], 2)
        assert chunks == [[1, 2], [3, 4], [5]]

    def test_chunk_list_invalid_size(self):
        with pytest.raises(ValueError):
            chunk_list([1, 2], 0)

    def test_pick(self):
        d = {"a": 1, "b": 2, "c": 3}
        assert pick(d, ["a", "c"]) == {"a": 1, "c": 3}

    def test_pick_missing_keys_ignored(self):
        assert pick({"a": 1}, ["a", "missing"]) == {"a": 1}

    def test_omit(self):
        d = {"a": 1, "b": 2, "c": 3}
        assert omit(d, ["b"]) == {"a": 1, "c": 3}

    def test_omit_missing_keys_ignored(self):
        assert omit({"a": 1}, ["missing"]) == {"a": 1}
