"""Integration tests for authentication flow."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models import User


class TestUser(BaseModel):
    """Test user model for authentication testing."""
    
    email: str
    username: str
    password: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False
    
    def create_db_user(self, db: Session) -> User:
        """Create a user in the test database."""
        user = User(
            email=self.email,
            username=self.username,
            hashed_password=get_password_hash(self.password),
            full_name=self.full_name,
            is_active=self.is_active,
            is_superuser=self.is_superuser,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# Test users with different scenarios
TEST_USERS = {
    "active_user": TestUser(
        email="active@example.com",
        username="activeuser",
        password="testpass123",
        full_name="Active User",
        is_active=True,
    ),
    "inactive_user": TestUser(
        email="inactive@example.com",
        username="inactiveuser",
        password="testpass123",
        full_name="Inactive User",
        is_active=False,
    ),
    "superuser": TestUser(
        email="admin@example.com",
        username="admin",
        password="adminpass123",
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    ),
}


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.parametrize(
        "test_name, username, password, expected_status, expected_detail",
        [
            # Test cases for login endpoint
            ("valid_credentials", "test@example.com", "testpassword", 200, None),
            ("invalid_password", "test@example.com", "wrongpassword", 401, "Incorrect email or password"),
            ("nonexistent_user", "nonexistent@example.com", "anypass", 401, "Incorrect email or password"),
            ("inactive_user", "inactive@example.com", "testpass123", 400, "Inactive user"),
            ("empty_username", "", "anypass", 422, None),  # Pydantic validation error
            ("empty_password", "test@example.com", "", 422, None),  # Pydantic validation error
        ]
    )
    def test_login_parameterized(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session,
        test_name: str,
        username: str,
        password: str,
        expected_status: int,
        expected_detail: Optional[str],
    ) -> None:
        """Test login endpoint with different scenarios."""
        # Create an inactive user for testing
        if username == "inactive@example.com":
            inactive_user = User(
                email="inactive@example.com",
                hashed_password=get_password_hash("testpass123"),
                is_active=False,
            )
            db_session.add(inactive_user)
            db_session.commit()
        
        # Make the login request
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": username,
                "password": password,
            },
        )
        
        # Verify the response
        assert response.status_code == expected_status
        response_data = response.json()
        
        if expected_status == 200:
            # Verify successful login response
            assert "access_token" in response_data
            assert response_data["token_type"] == "bearer"
            assert "expires_in" in response_data
        elif expected_status == 400 and expected_detail:
            # Verify error response for known error cases
            assert expected_detail in response_data["detail"]
        elif expected_status == 401 and expected_detail:
            # Verify unauthorized response
            assert expected_detail in response_data["detail"]
        
        # Clean up
        if username == "inactive@example.com":
            db_session.delete(inactive_user)
            db_session.commit()

    def test_read_users_me_authenticated(
        self, authorized_client: TestClient, test_user: User
    ) -> None:
        """Test accessing protected endpoint with valid token."""
        response = authorized_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert "hashed_password" not in data

    def test_read_users_me_unauthenticated(self, client: TestClient) -> None:
        """Test accessing protected endpoint without authentication."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_read_users_me_expired_token(self, client: TestClient, test_user: User) -> None:
        """Test accessing protected endpoint with expired token."""
        # Create an expired token
        expired_token = create_access_token(
            subject=test_user.email, expires_delta=-1
        )
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        
        assert response.status_code == 401
        assert "Token has expired" in response.json()["detail"]

    @pytest.mark.parametrize(
        "test_name, user_data, expected_status, expected_detail",
        [
            (
                "valid_registration",
                {
                    "email": "newuser@example.com",
                    "password": "newpass123",
                    "full_name": "New User"
                },
                200,
                None
            ),
            (
                "duplicate_email",
                {
                    "email": "active@example.com",  # Already exists
                    "password": "pass123",
                    "full_name": "Duplicate Email"
                },
                400,
                "Email already registered"
            ),
            (
                "missing_fields",
                {"email": "incomplete@example.com"},  # Missing required fields
                422,
                None  # Pydantic validation error
            ),
            (
                "invalid_email",
                {
                    "email": "not-an-email",
                    "password": "pass123",
                    "full_name": "Invalid Email"
                },
                422,
                None  # Pydantic validation error
            ),
        ],
    )
    def test_register_parameterized(
        self, client: TestClient, test_name: str, user_data: Dict[str, str], expected_status: int, expected_detail: str
    ) -> None:
        """Test registration endpoint with different scenarios."""
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == expected_status
        if expected_detail:
            assert expected_detail in response.json()["detail"]

    def test_register_user_success(self, client: TestClient) -> None:
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User",
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_user_duplicate_email(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test registration with duplicate email."""
        user_data = {
            "email": test_user.email,  # Duplicate email
            "password": "password123",
            "full_name": "Duplicate User",
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_user_invalid_email(self, client: TestClient) -> None:
        """Test registration with invalid email format."""
        user_data = {
            "email": "not-an-email",
            "password": "password123",
            "full_name": "Invalid Email",
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error
        assert "value is not a valid email address" in str(response.json())
