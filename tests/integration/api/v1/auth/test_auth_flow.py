"""Integration tests for authentication flow."""

import os
from typing import Dict, Optional

import pytest
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
# Use 'web' as the hostname when running in Docker Compose
BASE_URL = os.getenv("API_BASE_URL", "http://web:8000")
API_PREFIX = "/api/v1"

# Test user credentials
TEST_USER = {
    "email": "testuser@example.com",
    "username": "testuser",
    "password": "testpassword123",
    "full_name": "Test User",
}


class TestAuthFlow:
    """Test the authentication flow of the application."""

    @pytest.fixture(scope="class")
    def test_user(self) -> Dict[str, str]:
        """Return test user data."""
        return TEST_USER.copy()

    def make_request(
        self, method: str, endpoint: str, token: Optional[str] = None, **kwargs
    ) -> Dict:
        """Make an HTTP request to the API."""
        url = f"{BASE_URL}{API_PREFIX}{endpoint}"

        # Get any existing headers from kwargs or initialize empty dict
        headers = kwargs.pop("headers", {})

        # Add auth header if token is provided
        if token:
            headers["Authorization"] = f"Bearer {token}"

        print(f"\nMaking {method.upper()} request to {endpoint}")
        response = requests.request(method, url, headers=headers, **kwargs)

        print(f"Status Code: {response.status_code}")
        try:
            response_data = response.json()
            print("Response:", response_data)
        except ValueError:
            print("Response: (non-JSON)")
            response_data = {}

        return response_data

    def test_user_registration(self, test_user: Dict[str, str]) -> None:
        """Test user registration."""
        # First, try to register a new user
        response = self.make_request("POST", "/auth/register", json=test_user)

        if response.get("detail") == "Email already registered":
            print("User already exists, continuing with login...")
            return

        assert response.get("id") is not None, "User ID not in response"
        assert response.get("email") == test_user["email"], "Email mismatch"

    def test_user_login(self, test_user: Dict[str, str]) -> str:
        """Test user login and return the access token."""
        response = self.make_request(
            "POST",
            "/auth/login/access-token",
            data={
                "username": test_user["email"],
                "password": test_user["password"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert "access_token" in response, "Access token not in response"
        assert response["token_type"] == "bearer", "Invalid token type"

        return response["access_token"]

    def test_protected_endpoints(self, test_user: Dict[str, str]) -> None:
        """Test access to protected endpoints."""
        # First get a valid token
        token = self.test_user_login(test_user)

        # Test access to user profile
        response = self.make_request("GET", "/users/me", token=token)
        assert (
            response.get("email") == test_user["email"]
        ), "User email mismatch"

        # Test access to protected files endpoint
        response = self.make_request("GET", "/files/", token=token)
        assert isinstance(response, list), "Expected a list of files"

    def test_full_auth_flow(self, test_user: Dict[str, str]) -> None:
        """Test the full authentication flow in one test."""
        # Test registration
        self.test_user_registration(test_user)

        # Test login
        token = self.test_user_login(test_user)

        # Test protected endpoints
        self.test_protected_endpoints(test_user)

        # If we get here without exceptions, all tests passed
        assert True
