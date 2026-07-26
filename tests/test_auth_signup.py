import pytest
from pydantic import ValidationError

from backend.auth import SignupRequest


def test_signup_requires_matching_confirm_password() -> None:
    with pytest.raises(ValidationError):
        SignupRequest(
            full_name="Jane Doe",
            email="jane@example.com",
            password="secret123",
            confirm_password="other123",
        )
