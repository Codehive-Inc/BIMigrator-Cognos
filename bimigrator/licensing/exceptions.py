"""Exceptions for the BIMigrator licensing system."""


class LicenseError(Exception):
    """Base exception for all licensing errors."""
    pass


class LicenseExpiredError(LicenseError):
    """Exception raised when the license has expired."""
    def __init__(self, message="License has expired", expires_at=None):
        self.expires_at = expires_at
        if expires_at:
            message = f"{message} (Expired on: {expires_at})"
        super().__init__(message)


class LicenseLimitError(LicenseError):
    """Exception raised when the migration limit has been reached."""
    def __init__(self, message="Migration limit reached", used=None, limit=None):
        self.used = used
        self.limit = limit
        if used is not None and limit is not None:
            message = f"{message} (Used: {used}, Limit: {limit})"
        super().__init__(message)


class LicenseConnectionError(LicenseError):
    """Exception raised when there is an error connecting to the license database."""
    pass


class LicenseNotFoundError(LicenseError):
    """Exception raised when no valid license is found."""
    pass
