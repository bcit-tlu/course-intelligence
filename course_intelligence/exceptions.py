"""Shared exceptions across the course_intelligence package."""


class JobTimeout(Exception):
    """Raised when a job exceeds the configured execution timeout."""
