"""Shared Pydantic types and validators across domain modules."""
import re
from typing import Annotated

from pydantic import AfterValidator

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _validate_email_format(value: str) -> str:
    if not value or not isinstance(value, str):
        raise ValueError("Email address is required.")
    cleaned = value.strip().lower()
    if len(cleaned) > 255 or not EMAIL_REGEX.match(cleaned):
        raise ValueError(f"Invalid email address format: '{value}'")
    return cleaned


EmailAddress = Annotated[str, AfterValidator(_validate_email_format)]

