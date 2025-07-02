"""Unit tests for base schemas."""

from datetime import datetime, timezone
from typing import Optional

from app.schemas.base import TimestampMixin


def test_timestamp_mixin_ensure_tzinfo():
    """Test the ensure_tzinfo validator in TimestampMixin."""
    # Test with None
    assert TimestampMixin.ensure_tzinfo(None) is None

    # Test with timezone-aware datetime
    aware_dt = datetime.now(timezone.utc)
    assert TimestampMixin.ensure_tzinfo(aware_dt) == aware_dt

    # Test with timezone-naive datetime (should add UTC timezone)
    naive_dt = datetime(2023, 1, 1, 12, 0, 0)
    result = TimestampMixin.ensure_tzinfo(naive_dt)
    assert result.tzinfo is not None
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive_dt


def test_timestamp_mixin_set_timestamps():
    """Test the set_timestamps model validator in TimestampMixin."""
    # Test with empty dict (should add both timestamps)
    data = {}
    result = TimestampMixin.set_timestamps(data)
    assert "created_at" in result
    assert "updated_at" in result
    assert isinstance(result["created_at"], datetime)
    assert isinstance(result["updated_at"], datetime)

    # Test with existing timestamps (should not modify)
    now = datetime.now(timezone.utc)
    data = {"created_at": now, "updated_at": now}
    result = TimestampMixin.set_timestamps(data)
    assert result["created_at"] == now
    assert result["updated_at"] == now

    # Test with partial timestamps (should add missing ones)
    data = {"created_at": now}
    result = TimestampMixin.set_timestamps(data)
    assert result["created_at"] == now
    assert "updated_at" in result
    assert isinstance(result["updated_at"], datetime)

    data = {"updated_at": now}
    result = TimestampMixin.set_timestamps(data)
    assert result["updated_at"] == now
    assert "created_at" in result
    assert isinstance(result["created_at"], datetime)

    # Test with None values for timestamps (should replace with current time)
    data = {"created_at": None, "updated_at": None}
    result = TimestampMixin.set_timestamps(data)
    assert isinstance(result["created_at"], datetime)
    assert isinstance(result["updated_at"], datetime)
    assert result["created_at"] is not None
    assert result["updated_at"] is not None

    # Test with non-dict input (should return as-is)
    non_dict = "not a dict"
    result = TimestampMixin.set_timestamps(non_dict)
    assert result == non_dict


def test_timestamp_mixin_model_dump():
    """Test the model_dump method in TimestampMixin."""
    from datetime import datetime, timezone

    class TestModel(TimestampMixin):
        """Test model that uses TimestampMixin."""

        name: str

    # Create a model with timestamps
    now = datetime.now(timezone.utc)
    model = TestModel(name="test", created_at=now, updated_at=now)

    # Test model_dump
    result = model.model_dump()
    assert result["name"] == "test"
    assert result["created_at"] == now.isoformat()
    assert result["updated_at"] == now.isoformat()

    # Test with exclude_unset
    result = model.model_dump(exclude_unset=True)
    assert "name" in result
    assert "created_at" in result
    assert "updated_at" in result

    # Test with None values for timestamps
    # The set_timestamps validator will replace None with current time
    model = TestModel(name="test", created_at=None, updated_at=None)
    result = model.model_dump()
    assert result["name"] == "test"
    # Verify the timestamps were set to the current time and converted to ISO format
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)

    # Parse the ISO format strings back to datetime objects to verify they're valid
    created_at = datetime.fromisoformat(result["created_at"])
    updated_at = datetime.fromisoformat(result["updated_at"])

    # Verify the timestamps are recent (within the last minute)
    now = datetime.now(timezone.utc)
    assert (now - created_at).total_seconds() < 60
    assert (now - updated_at).total_seconds() < 60

    # Test with missing timestamp fields in the model
    # The set_timestamps validator will add them with current time
    model = TestModel(name="test")
    result = model.model_dump()
    assert result["name"] == "test"
    assert "created_at" in result
    assert "updated_at" in result
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)

    # Verify the timestamps are recent (within the last minute)
    created_at = datetime.fromisoformat(result["created_at"])
    updated_at = datetime.fromisoformat(result["updated_at"])
    now = datetime.now(timezone.utc)
    assert (now - created_at).total_seconds() < 60
    assert (now - updated_at).total_seconds() < 60

    # Test with a model that has a different set of fields
    # This will test the branch where timestamp fields are not in the data dictionary
    class AnotherModel(TimestampMixin):
        """Another test model that uses TimestampMixin but has no timestamp fields."""

        some_field: str

    model = AnotherModel(some_field="test")
    # The set_timestamps validator will add the timestamp fields
    result = model.model_dump()
    assert result["some_field"] == "test"
    assert "created_at" in result
    assert "updated_at" in result
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)

    # Test with a model that explicitly sets timestamp fields to None
    # This will test the branch where timestamp fields are in the data dictionary but are None
    class NullTimestampModel(TimestampMixin):
        """Test model with explicit None timestamps."""

        created_at: Optional[datetime] = None
        updated_at: Optional[datetime] = None

    # Create an instance with explicit None timestamps
    model = NullTimestampModel()
    # The set_timestamps validator will replace None with current time
    result = model.model_dump()
    assert "created_at" in result
    assert "updated_at" in result
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)

    # Test case specifically for covering lines 52-53 in base.py
    # where a field is in data but its value is None
    class TestModelWithNoneTimestamps(TimestampMixin):
        """Test model with explicit None timestamps for model_dump test."""

        created_at: Optional[datetime] = None
        updated_at: Optional[datetime] = None

    # Create a model instance and manually set the timestamps to None after initialization
    model = TestModelWithNoneTimestamps()
    # Override the timestamps to be None to test the branch in model_dump
    model.created_at = None
    model.updated_at = None
    # Call model_dump directly to test the specific branch
    result = model.model_dump()
    # The timestamps should still be in the result but as strings
    assert "created_at" in result
    assert "updated_at" in result


def test_timestamp_mixin_model_dump_json():
    """Test the model_dump_json method in TimestampMixin."""

    class TestModel(TimestampMixin):
        """Test model that uses TimestampMixin."""

        name: str

    # Create a model with timestamps
    now = datetime.now(timezone.utc)
    model = TestModel(name="test", created_at=now, updated_at=now)

    # Test model_dump_json
    json_str = model.model_dump_json()
    assert "name" in json_str
    assert "test" in json_str
    # The JSON output will use 'Z' for UTC timezone, so we need to check for that
    assert now.strftime("%Y-%m-%dT%H:%M:%S") in json_str
    assert "Z" in json_str  # Ensure UTC timezone is indicated with Z

    # Test with exclude_unset
    json_str = model.model_dump_json(exclude_unset=True)
    assert "name" in json_str
    assert "created_at" in json_str
    assert "updated_at" in json_str


def test_timestamp_mixin_with_validation():
    """Test that TimestampMixin works with Pydantic validation."""
    from pydantic import field_validator

    class TestModel(TimestampMixin):
        """Test model that uses TimestampMixin with validation."""

        name: str

        @field_validator("created_at", "updated_at", mode="before")
        @classmethod
        def parse_datetime_strings(cls, v):
            """Parse datetime strings into datetime objects."""
            if isinstance(v, str):
                # Handle both 'Z' and '+00:00' UTC timezone formats
                dt_str = v.replace("Z", "+00:00")
                try:
                    return datetime.fromisoformat(dt_str)
                except ValueError:
                    pass
            return v

    # Test creation with timestamps as strings
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    # Test with both 'Z' and '+00:00' timezone formats
    for timezone_format in [now_str, now_str.replace("+00:00", "Z")]:
        # Create model with string timestamps
        model = TestModel(
            name="test", created_at=timezone_format, updated_at=timezone_format
        )

        # Test that timestamps are properly converted to datetime objects
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

        # Compare timestamps without timezone info
        assert model.created_at.replace(tzinfo=None) == now.replace(
            tzinfo=None
        )
        assert model.updated_at.replace(tzinfo=None) == now.replace(
            tzinfo=None
        )

        # Test model_dump with timestamps
        result = model.model_dump()
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)

        # Test model_dump_json
        json_str = model.model_dump_json()
        assert now.strftime("%Y-%m-%dT%H:%M:%S") in json_str
        assert "Z" in json_str  # Ensure UTC timezone is indicated with Z
