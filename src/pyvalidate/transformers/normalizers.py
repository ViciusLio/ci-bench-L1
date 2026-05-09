"""
pyvalidate.transformers.normalizers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
String normalization helpers used in pipelines and schema transformations.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


# ---------------------------------------------------------------------------
# Core normalizers
# ---------------------------------------------------------------------------


def normalize_whitespace(value: str) -> str:
    """Collapse internal whitespace runs to a single space and strip edges."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    return re.sub(r"\s+", " ", value).strip()


def normalize_email(value: str) -> str:
    """Lowercase and strip an email address.

    Does not validate format — use EmailValidator for that.
    """
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    return value.strip().lower()


def normalize_url(value: str) -> str:
    """Lowercase the scheme and host of a URL, preserve path case."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    value = value.strip()
    if "://" in value:
        scheme, rest = value.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            return f"{scheme.lower()}://{host.lower()}/{path}"
        return f"{scheme.lower()}://{rest.lower()}"
    return value


def normalize_phone(value: str) -> str:
    """Strip all non-digit characters from a phone number, preserve leading +."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    value = value.strip()
    prefix = "+" if value.startswith("+") else ""
    digits = re.sub(r"\D", "", value)
    return prefix + digits


def slugify(value: str, *, separator: str = "-", max_length: Optional[int] = None) -> str:
    """Convert a string to a URL-safe slug.

    Steps:
    1. Normalize unicode to ASCII.
    2. Lowercase.
    3. Replace non-alphanumeric characters with *separator*.
    4. Collapse multiple separators.
    5. Strip leading/trailing separators.
    """
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    # Normalize unicode characters to their ASCII equivalents
    normalized = unicodedata.normalize("NFKD", value)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_str.lower()
    # Replace non-alphanumeric characters with separator
    slug = re.sub(r"[^a-z0-9]+", separator, lowered)
    slug = slug.strip(separator)
    if max_length:
        slug = slug[:max_length].rstrip(separator)
    return slug


def normalize_name(value: str) -> str:
    """Title-case a person's name, handling common edge cases (O'Brien, McDonald)."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    value = normalize_whitespace(value)
    parts = value.split(" ")
    normalized_parts = []
    for part in parts:
        if "-" in part:
            # Handle hyphenated names: Smith-Jones
            normalized_parts.append("-".join(p.capitalize() for p in part.split("-")))
        elif part.lower().startswith("mc") and len(part) > 2:
            normalized_parts.append("Mc" + part[2:].capitalize())
        elif part.lower().startswith("mac") and len(part) > 3:
            normalized_parts.append("Mac" + part[3:].capitalize())
        elif part.startswith("O'") and len(part) > 2:
            normalized_parts.append("O'" + part[2:].capitalize())
        else:
            normalized_parts.append(part.capitalize())
    return " ".join(normalized_parts)


def strip_html_tags(value: str) -> str:
    """Remove HTML tags from a string using a simple regex."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    clean = re.sub(r"<[^>]+>", "", value)
    return normalize_whitespace(clean)


def truncate_words(value: str, max_words: int, suffix: str = "...") -> str:
    """Truncate a string to at most *max_words* words."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    words = value.split()
    if len(words) <= max_words:
        return value
    return " ".join(words[:max_words]) + suffix


# ---------------------------------------------------------------------------
# Legacy helpers — kept for backwards compat
# NOTE: prefer the functions above; these will be removed in a future version.
# ---------------------------------------------------------------------------


def _legacy_clean_email(email: str) -> str:
    """legacy: kept for backwards compat — use normalize_email instead."""
    return email.strip().lower().replace(" ", "")


def _legacy_clean_phone(phone: str) -> str:
    """legacy: kept for backwards compat — use normalize_phone instead."""
    cleaned = ""
    for ch in phone:
        if ch.isdigit() or ch == "+":
            cleaned += ch
    return cleaned


def _legacy_to_slug(text: str) -> str:
    """legacy: kept for backwards compat — use slugify instead."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")
