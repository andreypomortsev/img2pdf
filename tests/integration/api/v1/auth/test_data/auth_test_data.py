"""Test data for authentication endpoint tests."""

from datetime import timedelta
from typing import Dict, List, Optional, TypedDict


class LoginTestData(TypedDict):
    """Type definition for login test data."""

    test_name: str
    username: str
    password: str
    expected_status: int
    expected_detail: Optional[str]


class RegistrationTestData(TypedDict):
    """Type definition for registration test data."""

    test_name: str
    user_data: Dict[str, str]
    expected_status: int
    expected_detail: Optional[str]


# Test cases for login endpoint
LOGIN_TEST_CASES: List[LoginTestData] = [
    {
        "test_name": "valid_credentials",
        "username": "test@example.com",
        "password": "testpassword",
        "expected_status": 200,
        "expected_detail": None,
    },
    {
        "test_name": "invalid_password",
        "username": "test@example.com",
        "password": "wrongpassword",
        "expected_status": 400,
        "expected_detail": "Incorrect email or password",
    },
    {
        "test_name": "nonexistent_user",
        "username": "nonexistent@example.com",
        "password": "anypass",
        "expected_status": 400,
        "expected_detail": "Incorrect email or password",
    },
    {
        "test_name": "inactive_user",
        "username": "inactive@example.com",
        "password": "testpass123",
        "expected_status": 400,
        "expected_detail": "Inactive user",
    },
    {
        "test_name": "empty_username",
        "username": "",
        "password": "anypass",
        "expected_status": 422,
        "expected_detail": None,
    },
    {
        "test_name": "empty_password",
        "username": "test@example.com",
        "password": "",
        "expected_status": 422,
        "expected_detail": None,
    },
]

# Test cases for registration endpoint
REGISTRATION_TEST_CASES: List[RegistrationTestData] = [
    {
        "test_name": "valid_registration",
        "user_data": {
            "email": "newuser@example.com",
            "password": "newpass123",
            "full_name": "New User",
        },
        "expected_status": 200,
        "expected_detail": None,
    },
    {
        "test_name": "duplicate_email",
        "user_data": {
            "email": "test@example.com",  # Already exists
            "password": "pass123",
            "full_name": "Duplicate Email",
        },
        "expected_status": 400,
        "expected_detail": "Email already registered",
    },
    {
        "test_name": "missing_fields",
        "user_data": {
            "email": "incomplete@example.com"
        },  # Missing required fields
        "expected_status": 422,
        "expected_detail": None,  # Pydantic validation error
    },
    {
        "test_name": "invalid_email",
        "user_data": {
            "email": "not-an-email",
            "password": "pass123",
            "full_name": "Invalid Email",
        },
        "expected_status": 422,
        "expected_detail": None,  # Pydantic validation error
    },
]

# Extract parameter names for pytest parametrize
LOGIN_PARAM_NAMES = (
    "test_name,username,password,expected_status,expected_detail"
)
REGISTRATION_PARAM_NAMES = (
    "test_name,user_data,expected_status,expected_detail"
)

# Convert test cases to parameter values
LOGIN_PARAM_VALUES = [
    (
        tc["test_name"],
        tc["username"],
        tc["password"],
        tc["expected_status"],
        tc["expected_detail"],
    )
    for tc in LOGIN_TEST_CASES
]

REGISTRATION_PARAM_VALUES = [
    (
        tc["test_name"],
        tc["user_data"],
        tc["expected_status"],
        tc["expected_detail"],
    )
    for tc in REGISTRATION_TEST_CASES
]

# Common test data
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword"
