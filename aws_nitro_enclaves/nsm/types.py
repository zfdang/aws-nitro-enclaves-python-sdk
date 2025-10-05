"""Data models used by the NSM SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Mapping, MutableMapping, Optional


@dataclass(frozen=True)
class PcrValue:
    """Represents the value of a single Platform Configuration Register slot."""

    slot: int
    digest: bytes
    locked: bool = False


@dataclass(frozen=True)
class AttestationDocument:
    """Placeholder for the attestation document structure.

    The concrete parsing logic will be implemented in a subsequent iteration once the
    native bindings expose real NSM attestation responses.
    """

    module_id: str
    timestamp: int
    digest: bytes
    pcrs: Mapping[int, PcrValue]
    certificate: Optional[bytes] = None
    cabundle: Optional[bytes] = None
    user_data: Optional[bytes] = None
    public_key: Optional[bytes] = None
    nonce: Optional[bytes] = None
    locked_pcrs: FrozenSet[int] = field(default_factory=frozenset)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AttestationDocument":
        module_id = str(payload["module_id"])
        timestamp = int(payload["timestamp"])
        digest = bytes(payload["digest"])

        locked_slots = {
            int(value) for value in payload.get("locked_pcrs", [])
        }

        pcr_map: Dict[int, PcrValue] = {}
        for slot, value in payload.get("pcrs", {}).items():
            slot_int = int(slot)
            digest_bytes = bytes(value)
            pcr_map[slot_int] = PcrValue(
                slot=slot_int,
                digest=digest_bytes,
                locked=slot_int in locked_slots,
            )

        def _optional_bytes(key: str) -> Optional[bytes]:
            value = payload.get(key)
            if value is None:
                return None
            return bytes(value)

        return cls(
            module_id=module_id,
            timestamp=timestamp,
            digest=digest,
            pcrs=pcr_map,
            certificate=_optional_bytes("certificate"),
            cabundle=_optional_bytes("cabundle"),
            user_data=_optional_bytes("user_data"),
            public_key=_optional_bytes("public_key"),
            nonce=_optional_bytes("nonce"),
            locked_pcrs=frozenset(locked_slots),
        )

    def to_dict(self) -> MutableMapping[str, object]:
        """Return a JSON-serialisable representation of the document."""

        return {
            "module_id": self.module_id,
            "timestamp": self.timestamp,
            "digest": self.digest.hex(),
            "pcrs": {slot: value.digest.hex() for slot, value in self.pcrs.items()},
            "certificate": self.certificate.decode("latin1") if self.certificate else None,
            "cabundle": self.cabundle.decode("latin1") if self.cabundle else None,
            "user_data": self.user_data.decode("latin1") if self.user_data else None,
            "public_key": self.public_key.decode("latin1") if self.public_key else None,
            "nonce": self.nonce.decode("latin1") if self.nonce else None,
            "locked_pcrs": sorted(self.locked_pcrs),
        }
