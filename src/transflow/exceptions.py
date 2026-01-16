"""Custom exceptions for TransFlow."""


class TransFlowException(Exception):
    """Base exception for all TransFlow errors."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class NetworkError(TransFlowException):
    """Network-related errors (retryable)."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=1)


class ValidationError(TransFlowException):
    """Validation errors (non-retryable)."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=2)


class ConfigurationError(TransFlowException):
    """Configuration errors."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=2)


class APIError(TransFlowException):
    """External API errors."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message, exit_code=exit_code)


class TranslationError(TransFlowException):
    """Translation-related errors."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=1)
