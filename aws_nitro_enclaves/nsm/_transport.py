"""Low-level transport backed by the Rust extension."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Optional

from .errors import (
    NsmAttestationError,
    NsmCertificateError,
    NsmDeviceNotFoundError,
    NsmError,
    NsmInvalidPcrError,
    NsmPcrLockedError,
    NsmRandomError,
    NsmSessionClosedError,
)

try:  # pragma: no cover - exercised indirectly in tests
    from . import _rust
except ImportError as exc:  # pragma: no cover - handled in tests via monkeypatch
    _rust = None  # type: ignore[assignment]
    _RUST_IMPORT_ERROR = exc
else:
    _RUST_IMPORT_ERROR = None


class RustUnavailableError(NsmError):
    """Raised when the Rust extension module cannot be imported."""


def _ensure_rust_available() -> None:
    if _rust is None:
        raise RustUnavailableError(
            "Rust extension aws_nitro_enclaves.nsm._rust is not available",
            cause=_RUST_IMPORT_ERROR,
        )


def _translate_runtime_error(error: RuntimeError) -> NsmError:
    message = str(error)
    if "does not exist" in message:
        return NsmDeviceNotFoundError(message, cause=error)
    if "session is closed" in message:
        return NsmSessionClosedError(message, cause=error)
    if "PCR slot" in message and "locked" not in message:
        return NsmInvalidPcrError(message, cause=error)
    if "locked" in message and "PCR" in message:
        return NsmPcrLockedError(message, cause=error)
    if "certificate" in message.lower():
        return NsmCertificateError(message, cause=error)
    if "attestation" in message.lower():
        return NsmAttestationError(message, cause=error)
    if "random" in message.lower():
        return NsmRandomError(message, cause=error)
    return NsmError(message, cause=error)


class NsmTransport(AbstractContextManager["NsmTransport"]):
    """Context manager around the Rust `NsmSession` object."""

    def __init__(self, device_path: Optional[str] = None) -> None:
        _ensure_rust_available()
        try:
            self._session = _rust.NsmSession(device_path=device_path)
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def __enter__(self) -> "NsmTransport":
        return self

    def __exit__(self, exc_type, exc, tb) -> Optional[bool]:
        self.close()
        return None

    def close(self) -> None:
        try:
            self._session.close()
        except RuntimeError as error:  # pragma: no cover - defensive guard
            raise _translate_runtime_error(error) from error

    @property
    def is_closed(self) -> bool:
        try:
            return bool(self._session.is_closed())
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    @property
    def device_path(self) -> str:
        try:
            return str(self._session.device_path())
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def get_random(self, length: int) -> bytes:
        try:
            return bytes(self._session.get_random(length))
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def describe_pcr_raw(self, slot: int) -> dict:
        try:
            return dict(self._session.describe_pcr_raw(slot))
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def describe_pcr(self, slot: int) -> bytes:
        return bytes(self.describe_pcr_raw(slot)["digest"])

    def extend_pcr(self, slot: int, data: bytes) -> bytes:
        try:
            return bytes(self._session.extend_pcr(slot, data))
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def lock_pcr(self, slot: int) -> bool:
        try:
            return bool(self._session.lock_pcr(slot))
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def lock_pcrs(self, lock_range: int) -> bool:
        try:
            return bool(self._session.lock_pcrs(lock_range))
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def set_certificate(self, slot: int, certificate: bytes) -> None:
        try:
            self._session.set_certificate(slot, certificate)
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def describe_certificate(self, slot: int) -> bytes:
        try:
            return bytes(self._session.describe_certificate(slot))
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def remove_certificate(self, slot: int) -> None:
        try:
            self._session.remove_certificate(slot)
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def describe_nsm(self) -> dict:
        try:
            return dict(self._session.describe_nsm())
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def get_attestation(
        self,
        *,
        user_data: Optional[bytes] = None,
        public_key: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> dict:
        try:
            return dict(
                self._session.get_attestation(user_data, public_key, nonce)
            )
        except RuntimeError as error:
            raise _translate_runtime_error(error) from error

    def get_attestation_raw(
        self,
        *,
        user_data: Optional[bytes] = None,
        public_key: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> dict:
        return self.get_attestation(
            user_data=user_data, public_key=public_key, nonce=nonce
        )


def sdk_version() -> str:
    """Return the version of the compiled Rust extension."""

    _ensure_rust_available()
    return str(_rust.sdk_version())


def default_device_path() -> str:
    _ensure_rust_available()
    return str(_rust.default_device_path())
