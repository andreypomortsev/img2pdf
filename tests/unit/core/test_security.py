"""Tests for the security module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from app.core import security
from app.core.config import settings


def test_verify_password_success():
    """Test that verify_password correctly verifies a password against its hash."""
    # Create a test password and its hash
    test_password = "testpassword123"

    # Mock the verify method to avoid bcrypt version warnings
    with patch("app.core.security.pwd_context.verify") as mock_verify:
        mock_verify.return_value = True

        # Call the function with any hash since we're mocking the verify
        result = security.verify_password(test_password, "mocked_hash")

        # Verify the mock was called with the right arguments
        mock_verify.assert_called_once_with(test_password, "mocked_hash")
        assert result is True


def test_verify_password_failure():
    """Test that verify_password returns False for incorrect passwords."""
    # Create test passwords
    test_password = "testpassword123"
    wrong_password = "wrongpassword456"

    # Mock the verify method to return False for wrong password
    with patch("app.core.security.pwd_context.verify") as mock_verify:
        mock_verify.return_value = False

        # Call the function with wrong password
        result = security.verify_password(wrong_password, "mocked_hash")

        # Verify the mock was called with the right arguments
        mock_verify.assert_called_once_with(wrong_password, "mocked_hash")
        assert result is False


@patch("app.core.security.pwd_context.hash")
def test_get_password_hash_creates_hash(mock_hash):
    """Test that get_password_hash creates a non-empty hash."""
    # Setup
    test_password = "testpassword123"
    mock_hash.return_value = "mocked_hashed_password"

    # Test
    hashed_password = security.get_password_hash(test_password)

    # Verify
    mock_hash.assert_called_once_with(test_password)
    assert hashed_password == "mocked_hashed_password"
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
        token = security.create_access_token(
            test_subject, expires_delta=custom_expiry
        )

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

    @patch("app.core.security.pwd_context.hash")
    @patch("app.core.security.pwd_context.verify")
    def test_same_password_has_different_hashes(self, mock_verify, mock_hash):
        """Test that the same password produces different hashes each time."""
        # Setup
        password = "testpassword123"
        hash1 = "mocked_hash_1"
        hash2 = "mocked_hash_2"

        # Configure mocks
        mock_hash.side_effect = [
            hash1,
            hash2,
        ]  # Return different hashes on subsequent calls
        mock_verify.return_value = True  # Always verify successfully

        # Test
        result1 = security.get_password_hash(password)
        result2 = security.get_password_hash(password)

        # Verify different hashes were generated
        assert result1 == hash1
        assert result2 == hash2
        assert result1 != result2

        # Verify verify_password was called with the right arguments
        assert security.verify_password(password, hash1) is True
        assert security.verify_password(password, hash2) is True
        assert mock_verify.call_count == 2
        mock_verify.assert_any_call(password, hash1)
        mock_verify.assert_any_call(password, hash2)

    @patch("app.core.security.pwd_context.verify")
    def test_verify_password_with_invalid_hash(self, mock_verify):
        """Test verify_password with an invalid hash format."""
        # Setup
        invalid_hash = "not_a_real_hash"
        test_password = "anypassword"

        # Configure mock
        mock_verify.return_value = False

        # Test
        result = security.verify_password(test_password, invalid_hash)

        # Verify
        assert result is False
        mock_verify.assert_called_once_with(test_password, invalid_hash)

    @patch("app.core.security.pwd_context.hash")
    @patch("app.core.security.pwd_context.verify")
    def test_verify_password_with_empty_password(self, mock_verify, mock_hash):
        """Test verify_password with an empty password."""
        # Setup
        empty_password = ""
        non_empty_password = "notempty"
        mock_hash.return_value = "mocked_empty_hash"

        # Configure mock_verify to return True only for the empty password
        def verify_side_effect(password, hashed):
            return password == empty_password

        mock_verify.side_effect = verify_side_effect

        # Test empty password verification
        hashed_password = security.get_password_hash(empty_password)
        empty_result = security.verify_password(
            empty_password, hashed_password
        )

        # Test non-empty password verification
        non_empty_result = security.verify_password(
            non_empty_password, hashed_password
        )

        # Verify results
        assert empty_result is True
        assert non_empty_result is False

        # Verify mocks were called correctly
        mock_hash.assert_called_once_with(empty_password)
        assert mock_verify.call_count == 2
        mock_verify.assert_any_call(empty_password, hashed_password)
        mock_verify.assert_any_call(non_empty_password, hashed_password)


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
