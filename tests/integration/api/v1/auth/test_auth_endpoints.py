"""Integration tests for authentication endpoints."""

from datetime import timedelta
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User
from tests.integration.api.v1.auth.test_data.auth_test_data import (
    LOGIN_PARAM_NAMES, LOGIN_PARAM_VALUES, REGISTRATION_PARAM_NAMES,
    REGISTRATION_PARAM_VALUES, TEST_USER_EMAIL, TEST_USER_PASSWORD)


class TestAuthEndpoints:
    """Test authentication endpoints.

    This test class covers all authentication-related endpoints including:
    - Login with access token
    - User registration
    - User profile access
    - Token validation
    """

    @pytest.mark.parametrize(
        LOGIN_PARAM_NAMES,
        LOGIN_PARAM_VALUES,
        ids=[tc[0] for tc in LOGIN_PARAM_VALUES],
    )
    def test_login_parameterized(
        self,
        client: TestClient,
        test_user: User,
        inactive_user: User,
        test_name: str,
        username: str,
        password: str,
        expected_status: int,
        expected_detail: Optional[str],
    ) -> None:
        """Test login endpoint with different scenarios.

        Test cases include:
        - Valid credentials
        - Invalid password
        - Nonexistent user
        - Inactive user
        - Empty username/password
        - Various edge cases
        """
        # Make the login request
        response = client.post(
            "/api/v1/auth/login/access-token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Verify the response
        assert response.status_code == expected_status, (
            f"Expected status {expected_status} but got {response.status_code}. "
            f"Response: {response.json()}"
        )

        response_data = response.json()

        if expected_status == 200:
            assert (
                "access_token" in response_data
            ), "Access token not in response"
            assert (
                response_data["token_type"] == "bearer"
            ), "Invalid token type"
        elif expected_status == 400 and expected_detail:
            assert expected_detail in response_data.get(
                "detail", ""
            ), "Unexpected error detail"
        elif expected_status == 422:  # Validation error
            assert (
                "detail" in response_data
            ), "Expected error details in response"

    def test_read_users_me_authenticated(
        self, authorized_client: TestClient
    ) -> None:
        """Test accessing protected endpoint with valid token."""
        response = authorized_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "hashed_password" not in data

    def test_read_users_me_unauthenticated(self, client: TestClient) -> None:
        """Test accessing protected endpoint without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_read_users_me_expired_token(self, client: TestClient) -> None:
        """Test accessing protected endpoint with expired token."""
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(minutes=-5),
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert "Token has expired" in response.json()["detail"]

    @pytest.mark.parametrize(
        REGISTRATION_PARAM_NAMES,
        REGISTRATION_PARAM_VALUES,
        ids=[tc[0] for tc in REGISTRATION_PARAM_VALUES],
    )
    def test_register_parameterized(
        self,
        client: TestClient,
        test_name: str,
        user_data: Dict[str, str],
        expected_status: int,
        expected_detail: Optional[str],
    ) -> None:
        """Test registration endpoint with different scenarios.

        Test cases include:
        - Valid registration
        - Duplicate email
        - Missing required fields
        - Invalid email format
        """
        response = client.post(
            "/api/v1/auth/register",
            json=user_data,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == expected_status, (
            f"Expected status {expected_status} but got {response.status_code}. "
            f"Response: {response.json()}"
        )

        response_data = response.json()

        if expected_status == 200:
            assert "id" in response_data, "User ID not in response"
            assert response_data["email"] == user_data["email"]
            assert response_data["is_active"] is True
            assert "hashed_password" not in response_data
        elif expected_status >= 400 and expected_detail:
            assert expected_detail in response_data.get(
                "detail", ""
            ), "Unexpected error detail"

    def test_read_users_me_with_valid_token(
        self, authorized_client: TestClient
    ) -> None:
        """Test accessing user profile with valid authentication token."""
        response = authorized_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER_EMAIL
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data

    def test_read_users_me_with_invalid_token(
        self, client: TestClient
    ) -> None:
        """Test accessing user profile with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_read_users_me_with_expired_token(
        self, client: TestClient
    ) -> None:
        """Test accessing user profile with expired token."""
        # Create an expired token (5 minutes in the past)
        expired_token = create_access_token(
            data={"sub": TEST_USER_EMAIL},
            expires_delta=timedelta(minutes=-5),
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        assert "Token has expired" in response.json()["detail"]

    def test_read_users_me_without_token(self, client: TestClient) -> None:
        """Test accessing user profile without any authentication token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_refresh_token(self, client: TestClient, test_user: User) -> None:
        """Test token refresh endpoint."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login/access-token",
            data={"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh the token
        refresh_response = client.post(
            "/api/v1/auth/login/refresh-token",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"

        # Verify the new access token works
        new_token = refresh_data["access_token"]
        me_response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == TEST_USER_EMAIL
