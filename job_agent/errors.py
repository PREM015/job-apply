class JobAgentError(Exception):
    """Base error for the application."""


class SafetyLockError(JobAgentError):
    """Raised whenever a live or unsafe action is requested."""


class ConfigError(JobAgentError):
    """Raised for invalid or unsafe configuration."""


class ValidationError(JobAgentError):
    """Raised when input cannot be validated."""
