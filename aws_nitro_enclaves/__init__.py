"""AWS Nitro Enclaves Python SDK."""

from importlib import metadata

from . import nsm  # noqa: F401

try:
    __version__ = metadata.version("aws-nitro-enclaves-python-sdk")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev
    __version__ = "0.0.0"

__all__ = ["nsm", "__version__"]
