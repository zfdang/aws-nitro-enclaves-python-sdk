"""Low-level transport backed by the CFFI extension."""

from __future__ import annotations

import hashlib
import time
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

from importlib import metadata

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
    from . import _native
except ImportError as exc:  # pragma: no cover - handled in tests via monkeypatch
    _native = None  # type: ignore[assignment]
    _NATIVE_IMPORT_ERROR = exc
else:
    _NATIVE_IMPORT_ERROR = None
    ffi = _native.ffi
    lib = _native.lib


DEFAULT_DEVICE_PATH = "/var/run/nsm"
PCR_SLOTS = 32
PCR_DIGEST_LEN = 32
CERTIFICATE_SLOTS = 4


class NativeUnavailableError(NsmError):
    """Raised when the CFFI extension module cannot be imported."""


def _ensure_native_available() -> None:
    if _native is None:
        raise NativeUnavailableError(
            "CFFI extension aws_nitro_enclaves.nsm._native is not available",
            cause=_NATIVE_IMPORT_ERROR,
        )


def _raise_error(
    code: int,
    *,
    context: str,
    slot: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    if code == lib.NSM_OK:
        return

    message = details or "Operation failed"
    if code == lib.NSM_ERR_CLOSED:
        raise NsmSessionClosedError("NSM session is closed")
    if code == lib.NSM_ERR_NO_MEMORY:
        raise NsmError("NSM native module was unable to allocate memory")
    if code == lib.NSM_ERR_INVALID_LENGTH:
        if context == "random":
            raise NsmRandomError("Random length must be greater than zero")
        if context == "certificate":
            raise NsmCertificateError("Certificate payload must not be empty")
        raise NsmError("Invalid length for native operation")
    if code == lib.NSM_ERR_LOCKED:
        raise NsmPcrLockedError(
            f"PCR slot {slot if slot is not None else '?'} is locked"
        )
    if code == lib.NSM_ERR_CERT_MISSING:
        raise NsmCertificateError("Certificate slot is empty")
    if code == lib.NSM_ERR_INVALID_SLOT:
        if context == "pcr":
            raise NsmInvalidPcrError(
                f"PCR slot {slot if slot is not None else '?'} is out of range"
            )
        raise NsmCertificateError(
            f"Certificate slot {slot if slot is not None else '?'} is out of range"
        )

    raise NsmError(message)


class NsmTransport(AbstractContextManager["NsmTransport"]):
    """Context manager around the native NSM session."""

    def __init__(self, device_path: Optional[str] = None) -> None:
        _ensure_native_available()

        path = Path(device_path or DEFAULT_DEVICE_PATH)
        self._device_path = str(path)
        if not path.exists():
            raise NsmDeviceNotFoundError(
                f"the NSM device path '{path}' does not exist"
            )

        raw_session = lib.nsm_session_new()
        if raw_session == ffi.NULL:
            raise NsmError("Failed to initialise NSM session")
        self._session = ffi.gc(raw_session, lib.nsm_session_free)
        self._certificates: Dict[int, bool] = {}

    def __enter__(self) -> "NsmTransport":
        return self

    def __exit__(self, exc_type, exc, tb) -> Optional[bool]:
        self.close()
        return None

    def close(self) -> None:
        code = lib.nsm_session_close(self._session)
        if code not in (lib.NSM_OK, lib.NSM_ERR_CLOSED):
            _raise_error(code, context="general")

    @property
    def is_closed(self) -> bool:
        return bool(lib.nsm_session_is_closed(self._session))

    @property
    def device_path(self) -> str:
        return self._device_path

    def get_random(self, length: int) -> bytes:
        buffer = ffi.new("unsigned char[]", length)
        code = lib.nsm_get_random(self._session, buffer, length)
        _raise_error(code, context="random")
        return bytes(ffi.buffer(buffer, length))

    def describe_pcr_raw(self, slot: int) -> Dict[str, object]:
        buffer = ffi.new("unsigned char[]", PCR_DIGEST_LEN)
        code = lib.nsm_describe_pcr(self._session, slot, buffer)
        _raise_error(code, context="pcr", slot=slot)
        locked = self._slot_locked(slot)
        return {
            "index": slot,
            "digest": bytes(ffi.buffer(buffer, PCR_DIGEST_LEN)),
            "locked": locked,
        }

    def describe_pcr(self, slot: int) -> bytes:
        return bytes(self.describe_pcr_raw(slot)["digest"])

    def extend_pcr(self, slot: int, data: bytes) -> bytes:
        buffer = ffi.new("unsigned char[]", PCR_DIGEST_LEN)
        code = lib.nsm_extend_pcr(self._session, slot, data, len(data), buffer)
        _raise_error(code, context="pcr", slot=slot)
        return bytes(ffi.buffer(buffer, PCR_DIGEST_LEN))

    def lock_pcr(self, slot: int) -> bool:
        code = lib.nsm_lock_pcr(self._session, slot)
        _raise_error(code, context="pcr", slot=slot)
        return True

    def lock_pcrs(self, lock_range: int) -> bool:
        code = lib.nsm_lock_range(self._session, lock_range)
        _raise_error(code, context="pcr")
        return True

    def set_certificate(self, slot: int, certificate: bytes) -> None:
        code = lib.nsm_set_certificate(
            self._session,
            slot,
            certificate,
            len(certificate),
        )
        _raise_error(code, context="certificate", slot=slot)
        self._certificates[slot] = True

    def describe_certificate(self, slot: int) -> bytes:
        out_ptr = ffi.new("const unsigned char **")
        out_len = ffi.new("size_t *")
        code = lib.nsm_describe_certificate(self._session, slot, out_ptr, out_len)
        _raise_error(code, context="certificate", slot=slot)
        data = bytes(ffi.buffer(out_ptr[0], out_len[0]))
        self._certificates[slot] = True
        return data

    def remove_certificate(self, slot: int) -> None:
        code = lib.nsm_remove_certificate(self._session, slot)
        _raise_error(code, context="certificate", slot=slot)
        self._certificates.pop(slot, None)

    def describe_nsm(self) -> Dict[str, object]:
        module_id = self._module_id()
        locked = [index for index, state in enumerate(self._locked_flags()) if state]
        return {
            "module_id": module_id,
            "device_path": self.device_path,
            "pcr_slots": PCR_SLOTS,
            "certificate_slots": CERTIFICATE_SLOTS,
            "locked_pcrs": locked,
            "certificates": len(self._certificates),
        }

    def get_attestation(
        self,
        *,
        user_data: Optional[bytes] = None,
        public_key: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> Dict[str, object]:
        if self.is_closed:
            raise NsmSessionClosedError("NSM session is closed")

        try:
            pcrs = {index: self.describe_pcr(index) for index in range(PCR_SLOTS)}
            digest = self._attestation_digest(
                pcrs.values(), user_data, public_key, nonce
            )
            locked = [
                index for index, state in enumerate(self._locked_flags()) if state
            ]
        except NsmError as exc:
            raise NsmAttestationError("Unable to build attestation payload", cause=exc)

        payload: Dict[str, object] = {
            "module_id": self._module_id(),
            "timestamp": int(time.time()),
            "digest": digest,
            "pcrs": pcrs,
            "locked_pcrs": locked,
            "certificate": self._first_certificate(),
            "cabundle": None,
            "user_data": user_data,
            "public_key": public_key,
            "nonce": nonce,
        }
        return payload

    def get_attestation_raw(
        self,
        *,
        user_data: Optional[bytes] = None,
        public_key: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> Dict[str, object]:
        return self.get_attestation(
            user_data=user_data, public_key=public_key, nonce=nonce
        )

    def _module_id(self) -> str:
        pointer = lib.nsm_module_id(self._session)
        if pointer == ffi.NULL:
            raise NsmError("NSM session returned an empty module ID")
        return ffi.string(pointer).decode("ascii")

    def _locked_flags(self) -> Sequence[int]:
        buffer = ffi.new("unsigned char[]", PCR_SLOTS)
        code = lib.nsm_locked_flags(self._session, buffer, PCR_SLOTS)
        _raise_error(code, context="pcr")
        return list(bytes(ffi.buffer(buffer, PCR_SLOTS)))

    def _slot_locked(self, slot: int) -> bool:
        flags = self._locked_flags()
        if slot < 0 or slot >= len(flags):
            raise NsmInvalidPcrError(f"PCR slot {slot} is out of range")
        return bool(flags[slot])

    def _first_certificate(self) -> Optional[bytes]:
        for slot in range(CERTIFICATE_SLOTS):
            out_ptr = ffi.new("const unsigned char **")
            out_len = ffi.new("size_t *")
            code = lib.nsm_describe_certificate(self._session, slot, out_ptr, out_len)
            if code == lib.NSM_OK:
                return bytes(ffi.buffer(out_ptr[0], out_len[0]))
            if code == lib.NSM_ERR_CERT_MISSING:
                continue
            _raise_error(code, context="certificate", slot=slot)
        return None

    @staticmethod
    def _attestation_digest(
        pcr_values: Iterable[bytes],
        user_data: Optional[bytes],
        public_key: Optional[bytes],
        nonce: Optional[bytes],
    ) -> bytes:
        hasher = hashlib.sha256()
        for value in pcr_values:
            hasher.update(value)
        if user_data:
            hasher.update(user_data)
        if public_key:
            hasher.update(public_key)
        if nonce:
            hasher.update(nonce)
        return hasher.digest()


def sdk_version() -> str:
    _ensure_native_available()
    try:
        return metadata.version("aws-nitro-enclaves-python-sdk")
    except metadata.PackageNotFoundError:  # pragma: no cover - development fallback
        return "0.0.0"


def default_device_path() -> str:
    return DEFAULT_DEVICE_PATH
