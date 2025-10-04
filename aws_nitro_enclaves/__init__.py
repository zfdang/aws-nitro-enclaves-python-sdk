"""AWS Nitro Enclaves Python SDK."""

from . import nsm  # noqa: F401
from importlib import metadata

try:
    __version__ = metadata.version("aws-nitro-enclaves-python-sdk")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev
    __version__ = "0.0.0"

__all__ = ["nsm", "__version__"]
