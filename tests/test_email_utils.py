"""Tests for email token generation and verification."""

import os

# Set a test secret before importing the module
os.environ["VERIFY_SECRET"] = "test-secret-for-ci"

from src.api.email_utils import generate_verify_token, verify_token


class TestEmailTokens:
    def test_generate_and_verify(self):
        token = generate_verify_token("user-123")
        result = verify_token(token)
        assert result == "user-123"

    def test_invalid_token_format(self):
        assert verify_token("garbage") is None
        assert verify_token("") is None
        assert verify_token("a.b") is None

    def test_tampered_signature(self):
        token = generate_verify_token("user-123")
        parts = token.split(".")
        parts[2] = "0" * 64  # fake signature
        tampered = ".".join(parts)
        assert verify_token(tampered) is None

    def test_tampered_user_id(self):
        token = generate_verify_token("user-123")
        parts = token.split(".")
        parts[1] = "user-456"  # different user
        tampered = ".".join(parts)
        assert verify_token(tampered) is None

    def test_token_structure(self):
        token = generate_verify_token("user-abc")
        parts = token.split(".")
        assert len(parts) == 3
        # First part is hex timestamp
        int(parts[0], 16)
        # Second part is user_id
        assert parts[1] == "user-abc"
        # Third part is hex HMAC
        assert len(parts[2]) == 64
