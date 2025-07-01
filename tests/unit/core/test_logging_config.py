import logging
import logging.config
from unittest.mock import patch

from app.core.logging_config import LOGGING_CONFIG, setup_logging


def test_logging_config_structure():
    """Test the structure of the LOGGING_CONFIG dictionary."""
    # Check required top-level keys
    assert "version" in LOGGING_CONFIG
    assert "disable_existing_loggers" in LOGGING_CONFIG
    assert "formatters" in LOGGING_CONFIG
    assert "handlers" in LOGGING_CONFIG
    assert "root" in LOGGING_CONFIG

    # Check formatters configuration
    assert "default" in LOGGING_CONFIG["formatters"]
    assert "format" in LOGGING_CONFIG["formatters"]["default"]

    # Check handlers configuration
    assert "console" in LOGGING_CONFIG["handlers"]
    assert "class" in LOGGING_CONFIG["handlers"]["console"]
    assert "formatter" in LOGGING_CONFIG["handlers"]["console"]

    # Check root logger configuration
    assert "level" in LOGGING_CONFIG["root"]
    assert "handlers" in LOGGING_CONFIG["root"]


def test_setup_logging():
    """Test that setup_logging configures logging correctly."""
    # Mock the logging.config.dictConfig method
    with patch("logging.config.dictConfig") as mock_dict_config:
        # Call the setup function
        setup_logging()

        # Check that dictConfig was called with our config
        mock_dict_config.assert_called_once_with(LOGGING_CONFIG)


def test_logging_output():
    """Test that logging works as expected after setup."""
    # Setup logging
    setup_logging()

    # Create a memory handler to capture logs
    from io import StringIO

    stream = StringIO()

    # Get the root logger and add our handler
    logger = logging.getLogger()
    handler = logging.StreamHandler(stream)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Get a logger and log a test message
    test_logger = logging.getLogger("test_logger")
    test_message = "This is a test log message"
    test_logger.info(test_message)

    # Get the log output
    log_output = stream.getvalue().strip()

    # Check that the log message was captured
    assert test_message in log_output
    assert "test_logger" in log_output
    assert "INFO" in log_output


def test_logging_levels():
    """Test that different log levels work as expected."""
    # Setup logging
    setup_logging()

    # Create a memory handler to capture logs
    from io import StringIO

    stream = StringIO()

    # Get the root logger and add our handler
    logger = logging.getLogger()
    handler = logging.StreamHandler(stream)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Test that the default level is INFO
    assert logger.getEffectiveLevel() == logging.INFO

    # Test that DEBUG messages are not logged by default
    logger.debug("This is a debug message")
    assert "DEBUG" not in stream.getvalue()

    # Test that INFO and above messages are logged
    test_messages = [
        (logging.INFO, "This is an info message"),
        (logging.WARNING, "This is a warning message"),
        (logging.ERROR, "This is an error message"),
        (logging.CRITICAL, "This is a critical message"),
    ]

    for level, message in test_messages:
        stream.truncate(0)  # Clear the stream
        stream.seek(0)
        logger.log(level, message)
        log_output = stream.getvalue().strip()
        assert message in log_output
        assert logging.getLevelName(level) in log_output


def test_logging_format():
    """Test that the log format is as expected."""
    # Setup logging
    setup_logging()

    # Get a logger and log a test message
    logger = logging.getLogger("test_format")

    # Patch the handler to capture the formatted message
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        LOGGING_CONFIG["formatters"]["default"]["format"]
    )
    handler.setFormatter(formatter)

    # Create a memory handler to capture the formatted output
    from io import StringIO

    stream = StringIO()
    handler.stream = stream

    # Add the handler to the logger and log a message
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    test_message = "Test format message"
    logger.info(test_message)

    # Get the formatted output
    formatted_output = stream.getvalue()

    # Check that the output contains the expected components
    assert test_message in formatted_output
    assert "test_format" in formatted_output
    assert "INFO" in formatted_output
