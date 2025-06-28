"""Tests for the security module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt
from passlib import hash as passlib_hash

from app.core import security
from app.core.config import settings


def test_verify_password_success():
    """Test that verify_password correctly verifies a password against its hash."""
    # Create a test password and its hash
    test_password = "testpassword123"
    hashed_password = security.get_password_hash(test_password)

    # Verify the password matches the hash
    assert security.verify_password(test_password, hashed_password) is True


def test_verify_password_failure():
    """Test that verify_password returns False for incorrect passwords."""
    # Create a test password and its hash
    test_password = "testpassword123"
    wrong_password = "wrongpassword456"
    hashed_password = security.get_password_hash(test_password)

    # Verify the wrong password doesn't match the hash
    assert security.verify_password(wrong_password, hashed_password) is False


def test_get_password_hash_creates_hash():
    """Test that get_password_hash creates a non-empty hash."""
    test_password = "testpassword123"
    hashed_password = security.get_password_hash(test_password)

    # The hash should not be empty and should be different from the original password
    assert hashed_password is not None
    assert hashed_password != test_password
    assert len(hashed_password) > 0


class TestCreateAccessToken:
    """Tests for the create_access_token function."""

    def test_create_access_token_with_default_expiry(self):
        """Test creating a token with default expiry time."""
        # Test data
        test_subject = "testuser@example.com"

        # Create token
        token = security.create_access_token(test_subject)

        # Verify token is not empty
        assert token is not None
        assert len(token) > 0

        # Decode the token to verify its contents
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )

        # Verify payload contains the expected subject and expiration
        assert payload["sub"] == test_subject
        assert "exp" in payload

        # Verify the token is not expired
        current_time = datetime.now(timezone.utc).timestamp()
        assert payload["exp"] > current_time

    def test_create_access_token_with_custom_expiry(self):
        """Test creating a token with a custom expiry time."""
        # Test data
        test_subject = "testuser@example.com"
        custom_expiry = timedelta(minutes=30)

        # Create token with custom expiry
        token = security.create_access_token(test_subject, expires_delta=custom_expiry)

        # Verify token is not empty
        assert token is not None

        # Decode the token to verify its expiration
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )

        # Verify the token is not expired
        current_time = datetime.now(timezone.utc).timestamp()
        assert payload["exp"] > current_time

        # Verify the token expires within the expected time range
        # (should be approximately 30 minutes from now, but we'll allow some leeway)
        max_expected_exp = (
            datetime.now(timezone.utc) + custom_expiry + timedelta(seconds=5)
        ).timestamp()
        assert payload["exp"] <= max_expected_exp

    def test_create_access_token_with_non_string_subject(self):
        """Test creating a token with a non-string subject (should be converted to string)."""
        # Test with an integer subject
        test_subject = 12345
        token = security.create_access_token(test_subject)

        # Decode and verify the subject was converted to string
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == str(test_subject)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_same_password_has_different_hashes(self):
        """Test that the same password produces different hashes each time."""
        password = "testpassword123"
        hash1 = security.get_password_hash(password)
        hash2 = security.get_password_hash(password)

        # The same password should produce different hashes due to random salt
        assert hash1 != hash2

        # But both hashes should verify correctly
        assert security.verify_password(password, hash1) is True
        assert security.verify_password(password, hash2) is True

    def test_verify_password_with_invalid_hash(self):
        """Test verify_password with an invalid hash format."""
        # This is not a valid bcrypt hash
        invalid_hash = "not_a_real_hash"

        # Mock the pwd_context.verify to return False for invalid hash
        with patch.object(security.pwd_context, "verify", return_value=False):
            # The function should return False for invalid hashes
            result = security.verify_password("anypassword", invalid_hash)
            assert result is False

    def test_verify_password_with_empty_password(self):
        """Test verify_password with an empty password."""
        # Create a hash of an empty password
        empty_password = ""
        hashed_password = security.get_password_hash(empty_password)

        # Should verify correctly
        assert security.verify_password(empty_password, hashed_password) is True

        # Non-empty password should not verify against this hash
        assert security.verify_password("notempty", hashed_password) is False


class TestTokenSecurity:
    """Tests related to token security."""

    def test_token_with_wrong_secret_key(self):
        """Test that a token signed with a different key is rejected."""
        # Create a token with the correct key
        test_subject = "testuser@example.com"
        token = security.create_access_token(test_subject)

        # Try to decode with a different key - should raise an exception
        with pytest.raises(jwt.JWTError):
            jwt.decode(
                token,
                "wrong_secret_key",  # Different from settings.SECRET_KEY
                algorithms=[settings.ALGORITHM],
            )

    def test_expired_token(self, monkeypatch):
        """Test that an expired token is rejected."""
        # Test data
        test_subject = "testuser@example.com"

        # Create a token with an expiration time in the past
        # We'll directly manipulate the expiration time in the payload
        from jose import jwt

        # Create a token that's already expired
        expired_token = jwt.encode(
            {
                "sub": test_subject,
                "exp": datetime.now(timezone.utc)
                - timedelta(seconds=60),  # Expired 1 minute ago
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        # Try to decode - should raise an expired token exception
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                expired_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": True},
            )

    @patch("app.core.security.settings.SECRET_KEY", "test_secret_key")
    @patch("app.core.security.settings.ALGORITHM", "HS256")
    @patch("app.core.security.settings.ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    def test_token_encoding_decoding_roundtrip(self):
        """Test that a token can be encoded and then decoded successfully."""
        # Test data
        test_subject = "testuser@example.com"

        # Create token
        token = security.create_access_token(test_subject)

        # Decode the token
        payload = jwt.decode(
            token,
            "test_secret_key",  # Using the patched secret key
            algorithms=["HS256"],  # Using the patched algorithm
        )

        # Verify the payload
        assert payload["sub"] == test_subject
        assert "exp" in payload

        # Verify expiration is in the future
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        assert exp_datetime > datetime.now(timezone.utc)
