"""High-level client for the Nitro Secure Module."""

from __future__ import annotations

from typing import Callable, Optional

from . import _transport
from .errors import NsmError, NsmRandomError
from .types import AttestationDocument, PcrValue

TransportFactory = Callable[[Optional[str]], _transport.NsmTransport]


class NsmClient:
    """Blocking NSM client backed by the Rust transport."""

    def __init__(
        self,
        *,
        device_path: Optional[str] = None,
        transport_factory: Optional[TransportFactory] = None,
    ) -> None:
        self._device_path = device_path
        self._transport_factory = transport_factory or _transport.NsmTransport
        self._transport: Optional[_transport.NsmTransport] = None

    def __enter__(self) -> "NsmClient":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> Optional[bool]:
        self.close()
        return None

    @property
    def device_path(self) -> str:
        if self._transport is None:
            if self._device_path is not None:
                return self._device_path
            return _transport.default_device_path()
        return self._transport.device_path

    @property
    def is_open(self) -> bool:
        return self._transport is not None and not self._transport.is_closed

    def open(self) -> None:
        if self._transport is None or self._transport.is_closed:
            self._transport = self._transport_factory(self._device_path)

    def close(self) -> None:
        if self._transport is not None and not self._transport.is_closed:
            self._transport.close()

    def get_random(self, length: int) -> bytes:
        if length <= 0:
            raise NsmRandomError("length must be greater than zero")
        transport = self._require_transport()
        return transport.get_random(length)

    def describe_pcr(self, slot: int) -> PcrValue:
        if slot < 0:
            raise NsmError("PCR slot must be non-negative")
        transport = self._require_transport()
        raw = transport.describe_pcr_raw(slot)
        digest = bytes(raw["digest"])
        locked = bool(raw.get("locked", False))
        return PcrValue(slot=slot, digest=digest, locked=locked)

    def describe_pcr_raw(self, slot: int) -> dict:
        if slot < 0:
            raise NsmError("PCR slot must be non-negative")
        transport = self._require_transport()
        return transport.describe_pcr_raw(slot)

    def extend_pcr(self, slot: int, data: bytes) -> PcrValue:
        if slot < 0:
            raise NsmError("PCR slot must be non-negative")
        if not data:
            raise NsmError("data to extend must not be empty")
        transport = self._require_transport()
        digest = transport.extend_pcr(slot, data)
        locked = bool(transport.describe_pcr_raw(slot).get("locked", False))
        return PcrValue(slot=slot, digest=digest, locked=locked)

    def set_certificate(self, slot: int, certificate: bytes) -> None:
        if slot < 0:
            raise NsmError("certificate slot must be non-negative")
        if not certificate:
            raise NsmError("certificate payload must not be empty")
        transport = self._require_transport()
        transport.set_certificate(slot, certificate)

    def describe_certificate(self, slot: int) -> bytes:
        if slot < 0:
            raise NsmError("certificate slot must be non-negative")
        transport = self._require_transport()
        return transport.describe_certificate(slot)

    def remove_certificate(self, slot: int) -> None:
        if slot < 0:
            raise NsmError("certificate slot must be non-negative")
        transport = self._require_transport()
        transport.remove_certificate(slot)

    def lock_pcr(self, slot: int) -> bool:
        if slot < 0:
            raise NsmError("PCR slot must be non-negative")
        transport = self._require_transport()
        return transport.lock_pcr(slot)

    def lock_pcrs(self, lock_range: int) -> bool:
        if lock_range < 0:
            raise NsmError("lock range must be non-negative")
        transport = self._require_transport()
        return transport.lock_pcrs(lock_range)

    def get_attestation(
        self,
        *,
        user_data: Optional[bytes] = None,
        public_key: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> AttestationDocument:
        transport = self._require_transport()
        payload = transport.get_attestation(
            user_data=user_data,
            public_key=public_key,
            nonce=nonce,
        )
        return AttestationDocument.from_payload(payload)

    def get_attestation_raw(
        self,
        *,
        user_data: Optional[bytes] = None,
        public_key: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> dict:
        transport = self._require_transport()
        return transport.get_attestation_raw(
            user_data=user_data,
            public_key=public_key,
            nonce=nonce,
        )

    def describe_nsm(self) -> dict:
        transport = self._require_transport()
        return transport.describe_nsm()

    def _require_transport(self) -> _transport.NsmTransport:
        if self._transport is None:
            raise NsmError(
                "NSM client is not open. Call open() or use the context manager interface."
            )
        return self._transport

    @staticmethod
    def rust_sdk_version() -> str:
        """Expose the compiled Rust extension version."""

        return _transport.sdk_version()
