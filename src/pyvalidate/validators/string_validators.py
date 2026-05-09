"""
pyvalidate.validators.string_validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validators for string values: email, URL, regex, length, slug, UUID, IP address.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Optional
from pyvalidate.base import BaseValidator, ValidationResult

# ---------------------------------------------------------------------------
# Compiled patterns (module-level for performance)
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

_URL_PATTERN = re.compile(
    r"^(?:https?|ftp)://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9\-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|localhost|\d{1,3}(?:\.\d{1,3}){3})"
    r"(?::\d+)?(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_IPV4_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

_IPV6_PATTERN = re.compile(
    r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
)

_PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")


# ---------------------------------------------------------------------------
# EmailValidator
# ---------------------------------------------------------------------------


class EmailValidator(BaseValidator):
    """Validates that a string is a well-formed email address.

    Uses a compiled regex pattern matching the common subset of RFC 5322.
    Does NOT perform DNS MX record lookup.
    """

    error_code = "invalid_email"

    def __init__(
        self,
        *,
        allow_plus_addressing: bool = True,
        max_length: int = 254,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._allow_plus = allow_plus_addressing
        self._max_length = max_length

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return self._make_error(
                f"Expected a string, got {type(value).__name__}.", value=value
            )
        if len(value) > self._max_length:
            return self._make_error(
                f"Email must not exceed {self._max_length} characters.", value=value
            )
        if not self._allow_plus and "+" in value:
            return self._make_error(
                "Plus addressing is not allowed in email.", value=value
            )
        if not _EMAIL_PATTERN.match(value):
            return self._make_error(
                f"{value!r} is not a valid email address.", value=value
            )
        return ValidationResult.ok(value.lower())

    def __repr__(self) -> str:
        return (
            f"EmailValidator(allow_plus_addressing={self._allow_plus}, "
            f"max_length={self._max_length})"
        )


# ---------------------------------------------------------------------------
# URLValidator
# ---------------------------------------------------------------------------


class URLValidator(BaseValidator):
    """Validates that a string is a well-formed HTTP/HTTPS/FTP URL.

    Uses a compiled regex pattern for fast validation without network calls.
    """

    error_code = "invalid_url"

    def __init__(
        self,
        *,
        allowed_schemes: Optional[list[str]] = None,
        require_tld: bool = True,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._allowed_schemes = [s.lower() for s in allowed_schemes] if allowed_schemes else None
        self._require_tld = require_tld

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return self._make_error(
                f"Expected a string, got {type(value).__name__}.", value=value
            )
        value = value.strip()
        if not value:
            return self._make_error("URL must not be empty.", value=value)

        if self._allowed_schemes:
            scheme = value.split("://")[0].lower() if "://" in value else ""
            if scheme not in self._allowed_schemes:
                return self._make_error(
                    f"URL scheme must be one of: {', '.join(self._allowed_schemes)}.",
                    value=value,
                )

        if not _URL_PATTERN.match(value):
            return self._make_error(
                f"{value!r} is not a valid URL.", value=value
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return (
            f"URLValidator(allowed_schemes={self._allowed_schemes!r}, "
            f"require_tld={self._require_tld})"
        )


# ---------------------------------------------------------------------------
# RegexValidator
# ---------------------------------------------------------------------------


class RegexValidator(BaseValidator):
    """Validates that a string matches a given regular expression pattern.

    The pattern is compiled once at instantiation for performance.
    """

    error_code = "pattern_mismatch"

    def __init__(
        self,
        pattern: str,
        *,
        flags: int = 0,
        full_match: bool = True,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._raw_pattern = pattern
        self._compiled = re.compile(pattern, flags)
        self._full_match = full_match

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return self._make_error(
                f"Expected a string, got {type(value).__name__}.", value=value
            )
        matcher = self._compiled.fullmatch if self._full_match else self._compiled.search
        if not matcher(value):
            return self._make_error(
                f"{value!r} does not match pattern {self._raw_pattern!r}.",
                value=value,
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return (
            f"RegexValidator(pattern={self._raw_pattern!r}, "
            f"full_match={self._full_match})"
        )


# ---------------------------------------------------------------------------
# LengthValidator
# ---------------------------------------------------------------------------


class LengthValidator(BaseValidator):
    """Validates the length of a string, list, or any sized object.

    At least one of *min_length* or *max_length* must be provided.
    """

    error_code = "invalid_length"

    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        exact: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if exact is not None:
            min_length = max_length = exact
        self._min = min_length
        self._max = max_length

    def validate(self, value: Any) -> ValidationResult:
        try:
            length = len(value)
        except TypeError:
            return self._make_error(
                f"Value of type {type(value).__name__!r} has no length.", value=value
            )
        if self._min is not None and length < self._min:
            return self._make_error(
                f"Length {length} is below minimum {self._min}.", value=value
            )
        if self._max is not None and length > self._max:
            return self._make_error(
                f"Length {length} exceeds maximum {self._max}.", value=value
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"LengthValidator(min={self._min}, max={self._max})"


# ---------------------------------------------------------------------------
# SlugValidator
# ---------------------------------------------------------------------------


class SlugValidator(BaseValidator):
    """Validates that a string is a URL-safe slug (lowercase, digits, hyphens).

    Valid examples: ``my-project``, ``hello-world-123``.
    Uses a compiled regex for matching.
    """

    error_code = "invalid_slug"

    def __init__(
        self,
        *,
        max_length: int = 200,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._max_length = max_length

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return self._make_error(
                f"Expected a string, got {type(value).__name__}.", value=value
            )
        if len(value) > self._max_length:
            return self._make_error(
                f"Slug must not exceed {self._max_length} characters.", value=value
            )
        if not _SLUG_PATTERN.match(value):
            return self._make_error(
                f"{value!r} is not a valid slug. "
                "Use lowercase letters, digits and hyphens only.",
                value=value,
            )
        return ValidationResult.ok(value)

    def __repr__(self) -> str:
        return f"SlugValidator(max_length={self._max_length})"


# ---------------------------------------------------------------------------
# UUIDValidator
# ---------------------------------------------------------------------------


class UUIDValidator(BaseValidator):
    """Validates that a string is a valid UUID (v1–v5).

    Accepts both hyphenated and non-hyphenated forms.
    """

    error_code = "invalid_uuid"

    def __init__(
        self,
        *,
        version: Optional[int] = None,
        return_object: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._version = version
        self._return_object = return_object

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (str, uuid.UUID)):
            return self._make_error(
                f"Expected a string or UUID, got {type(value).__name__}.", value=value
            )
        try:
            parsed = uuid.UUID(str(value))
        except (ValueError, AttributeError):
            return self._make_error(
                f"{value!r} is not a valid UUID.", value=value
            )
        if self._version is not None and parsed.version != self._version:
            return self._make_error(
                f"Expected UUID version {self._version}, got version {parsed.version}.",
                value=value,
            )
        result_value = parsed if self._return_object else str(parsed)
        return ValidationResult.ok(result_value)

    def __repr__(self) -> str:
        return f"UUIDValidator(version={self._version})"


# ---------------------------------------------------------------------------
# IPAddressValidator
# ---------------------------------------------------------------------------


class IPAddressValidator(BaseValidator):
    """Validates IPv4 or IPv6 addresses using compiled regex patterns."""

    error_code = "invalid_ip"

    def __init__(
        self,
        *,
        protocol: str = "both",
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        if protocol not in ("ipv4", "ipv6", "both"):
            raise ValueError("protocol must be 'ipv4', 'ipv6', or 'both'")
        self._protocol = protocol

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return self._make_error(
                f"Expected a string, got {type(value).__name__}.", value=value
            )
        if self._protocol in ("ipv4", "both") and _IPV4_PATTERN.match(value):
            return ValidationResult.ok(value)
        if self._protocol in ("ipv6", "both") and _IPV6_PATTERN.match(value):
            return ValidationResult.ok(value)
        label = {"ipv4": "IPv4", "ipv6": "IPv6", "both": "IP"}.get(self._protocol, "IP")
        return self._make_error(
            f"{value!r} is not a valid {label} address.", value=value
        )

    def __repr__(self) -> str:
        return f"IPAddressValidator(protocol={self._protocol!r})"


# ---------------------------------------------------------------------------
# PhoneValidator
# ---------------------------------------------------------------------------


class PhoneValidator(BaseValidator):
    """Validates international phone numbers in E.164-like format.

    Uses a compiled regex pattern: optional leading +, 7–15 digits.
    """

    error_code = "invalid_phone"

    def __init__(
        self,
        *,
        strip_spaces: bool = True,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._strip_spaces = strip_spaces

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return self._make_error(
                f"Expected a string, got {type(value).__name__}.", value=value
            )
        normalized = value.replace(" ", "").replace("-", "") if self._strip_spaces else value
        if not _PHONE_PATTERN.match(normalized):
            return self._make_error(
                f"{value!r} is not a valid phone number.", value=value
            )
        return ValidationResult.ok(normalized)

    def __repr__(self) -> str:
        return f"PhoneValidator(strip_spaces={self._strip_spaces})"


# ---------------------------------------------------------------------------
# ChoiceValidator
# ---------------------------------------------------------------------------


class ChoiceValidator(BaseValidator):
    """Validates that a value is one of a fixed set of allowed choices."""

    error_code = "invalid_choice"

    def __init__(
        self,
        choices: list[Any],
        *,
        case_insensitive: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message=message)
        self._choices = choices
        self._case_insensitive = case_insensitive
        if case_insensitive:
            self._lookup = {str(c).lower(): c for c in choices}
        else:
            self._lookup = {c: c for c in choices}

    def validate(self, value: Any) -> ValidationResult:
        key = str(value).lower() if self._case_insensitive else value
        if key not in self._lookup:
            choices_str = ", ".join(repr(c) for c in self._choices)
            return self._make_error(
                f"{value!r} is not a valid choice. Choose from: {choices_str}.",
                value=value,
            )
        return ValidationResult.ok(self._lookup[key])

    def __repr__(self) -> str:
        return f"ChoiceValidator(choices={self._choices!r})"
