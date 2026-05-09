"""
pyvalidate.utils.helpers
~~~~~~~~~~~~~~~~~~~~~~~~~
Internal utility functions used across the pyvalidate package.
"""
from __future__ import annotations

import importlib
from typing import Any, Optional, Type


def is_empty(value: Any) -> bool:
    """Return True if *value* is considered empty.

    Empty means: None, empty string (after strip), empty list/dict/set/tuple.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict, set, frozenset, tuple)) and len(value) == 0:
        return True
    return False


def coerce_type(value: Any, target_type: Type, *, strict: bool = False) -> Any:
    """Attempt to coerce *value* to *target_type*.

    Parameters
    ----------
    strict:
        If True, raise TypeError instead of returning None on failure.
    """
    if isinstance(value, target_type):
        return value
    try:
        return target_type(value)
    except (ValueError, TypeError) as exc:
        if strict:
            raise TypeError(
                f"Cannot coerce {value!r} ({type(value).__name__}) "
                f"to {target_type.__name__}: {exc}"
            ) from exc
        return None


def safe_import(module_path: str, attribute: Optional[str] = None) -> Any:
    """Import a module (and optionally an attribute) without raising on error.

    Returns None if the import fails.
    """
    try:
        module = importlib.import_module(module_path)
        if attribute:
            return getattr(module, attribute, None)
        return module
    except ImportError:
        return None


def flatten_errors(errors: dict) -> list[str]:
    """Flatten a nested error dict to a flat list of ``field: message`` strings.

    Input::

        {"email": ["Invalid email"], "address": {"city": ["Required"]}}

    Output::

        ["email: Invalid email", "address.city: Required"]
    """
    result: list[str] = []

    def _flatten(obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                _flatten(val, f"{prefix}.{key}" if prefix else key)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, str):
                    result.append(f"{prefix}: {item}" if prefix else item)
                else:
                    _flatten(item, prefix)
        elif isinstance(obj, str):
            result.append(f"{prefix}: {obj}" if prefix else obj)

    _flatten(errors, "")
    return result


def format_error_path(parts: list[str]) -> str:
    """Join path parts into a dotted error path string.

    E.g.: ``["address", "city"]`` → ``"address.city"``
    """
    return ".".join(str(p) for p in parts if p is not None)


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def chunk_list(lst: list, size: int) -> list[list]:
    """Split *lst* into sub-lists of at most *size* items."""
    if size <= 0:
        raise ValueError("Chunk size must be positive.")
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def pick(data: dict, keys: list[str]) -> dict:
    """Return a new dict with only the specified *keys* from *data*."""
    return {k: data[k] for k in keys if k in data}


def omit(data: dict, keys: list[str]) -> dict:
    """Return a new dict with the specified *keys* removed from *data*."""
    skip = set(keys)
    return {k: v for k, v in data.items() if k not in skip}
