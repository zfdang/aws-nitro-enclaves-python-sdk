"""Public interface for interacting with the Nitro Secure Module (NSM)."""

from importlib import metadata

from .client import NsmClient
from .errors import (
    NsmError,
    NsmDeviceNotFoundError,
    NsmPcrLockedError,
    NsmSessionClosedError,
)

try:
    __version__ = metadata.version("aws-nitro-enclaves-python-sdk")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev
    __version__ = "0.0.0"


def sdk_version() -> str:
    """Return the version of the bundled native extension."""

    return NsmClient.sdk_version()


__all__ = [
    "NsmClient",
    "NsmError",
    "NsmDeviceNotFoundError",
    "NsmSessionClosedError",
    "NsmPcrLockedError",
    "sdk_version",
]
