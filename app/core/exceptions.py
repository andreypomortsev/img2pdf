"""Custom exceptions for the application."""


class AppError(Exception):
    """Base exception for all application-specific exceptions."""

    pass


class DatabaseError(AppError):
    """Raised when a database operation fails."""

    pass


class ServiceError(AppError):
    """Raised when a service operation fails due to business logic."""

    pass


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(ServiceError):
    """Raised when input validation fails."""

    pass


class UnauthorizedError(ServiceError):
    """Raised when a user is not authorized to perform an action."""

    pass
