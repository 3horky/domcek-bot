"""Stable domain-level errors independent of HTTP and persistence."""


class DomainValidationError(ValueError):
    """Raised when a domain value would violate an invariant."""


class OptimisticLockError(RuntimeError):
    """Raised when a stale editor version tries to overwrite a newer value."""
