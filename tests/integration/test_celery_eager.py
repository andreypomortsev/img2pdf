from app.tasks import test_task
from app.worker import celery_app


def test_celery_eager_mode():
    """Test that Celery tasks run eagerly in test mode."""
    # This test will fail if the Celery app is not properly configured for eager execution
    result = test_task.delay()

    # In eager mode, the task should complete immediately
    assert result.ready() is True, "Task did not complete immediately in eager mode"
    assert result.get() == "Test task completed", "Task did not return expected result"
    assert (
        result.status == "SUCCESS"
    ), f"Task status is {result.status}, expected SUCCESS"
