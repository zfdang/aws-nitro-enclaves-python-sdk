"""Exception hierarchy for the NSM SDK."""

from __future__ import annotations

from typing import Optional


class NsmError(Exception):
    """Base exception for all NSM-related failures."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


class NsmDeviceNotFoundError(NsmError):
    """Raised when the NSM device socket cannot be located."""


class NsmSessionClosedError(NsmError):
    """Raised when an operation is attempted on a closed session."""


class NsmRandomError(NsmError):
    """Raised when random bytes cannot be produced by the NSM."""


class NsmInvalidPcrError(NsmError):
    """Raised when an invalid PCR slot is requested."""


class NsmCertificateError(NsmError):
    """Raised when certificate management operations fail."""


class NsmAttestationError(NsmError):
    """Raised when attestation documents cannot be created or parsed."""


class NsmPcrLockedError(NsmError):
    """Raised when attempting to modify a locked PCR slot."""
