from __future__ import annotations

from pathlib import Path

import pytest

from aws_nitro_enclaves.nsm import NsmClient
from aws_nitro_enclaves.nsm.errors import (
    NsmCertificateError,
    NsmDeviceNotFoundError,
    NsmError,
    NsmInvalidPcrError,
    NsmPcrLockedError,
    NsmRandomError,
)


@pytest.fixture()
def fake_device(tmp_path: Path) -> str:
    sock = tmp_path / "nsm.sock"
    sock.touch()
    return str(sock)


def test_context_manager_opens_and_closes(fake_device: str) -> None:
    client = NsmClient(device_path=fake_device)
    assert not client.is_open
    with client as ctx:
        assert ctx is client
        assert client.is_open
        data = client.get_random(32)
        assert len(data) == 32
    assert not client.is_open


def test_get_random_requires_open(fake_device: str) -> None:
    client = NsmClient(device_path=fake_device)
    with pytest.raises(NsmError):
        client.get_random(8)


def test_get_random_validates_length(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        with pytest.raises(NsmRandomError):
            client.get_random(0)


def test_missing_device_path_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sock"
    client = NsmClient(device_path=str(missing))
    with pytest.raises(NsmDeviceNotFoundError):
        client.open()


def test_rust_sdk_version_matches_package() -> None:
    version = NsmClient.rust_sdk_version()
    assert isinstance(version, str)
    assert version


def test_describe_and_extend_pcr(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        original = client.describe_pcr(0)
        assert original.slot == 0
        assert original.digest == bytes([0] * 32)
        assert original.locked is False

        updated = client.extend_pcr(0, b"hello")
        assert updated.slot == 0
        assert updated.digest != original.digest
        assert updated.locked is False

        latest = client.describe_pcr(0)
        assert latest.digest == updated.digest
        assert latest.locked is False


def test_extend_pcr_rejects_empty_payload(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        with pytest.raises(NsmError):
            client.extend_pcr(0, b"")


def test_invalid_pcr_slot(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        with pytest.raises(NsmInvalidPcrError):
            client.describe_pcr(999)


def test_certificate_lifecycle(fake_device: str) -> None:
    cert = b"-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----"
    with NsmClient(device_path=fake_device) as client:
        client.set_certificate(0, cert)
        assert client.describe_certificate(0) == cert
        client.remove_certificate(0)
        with pytest.raises(NsmCertificateError):
            client.describe_certificate(0)


def test_get_attestation_returns_document(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        doc = client.get_attestation(user_data=b"payload", nonce=b"123")
        assert doc.module_id
        assert doc.timestamp > 0
        assert doc.digest
        assert doc.user_data == b"payload"
        assert doc.nonce == b"123"
        assert 0 in doc.pcrs
        assert not doc.locked_pcrs


def test_pcr_locking_prevents_extensions(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        client.lock_pcr(0)
        info = client.describe_pcr(0)
        assert info.locked is True
        with pytest.raises(NsmPcrLockedError):
            client.extend_pcr(0, b"later")


def test_lock_range_affects_prefix(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        client.lock_pcrs(2)
        assert client.describe_pcr(0).locked is True
        assert client.describe_pcr(1).locked is True
        assert client.describe_pcr(2).locked is False


def test_describe_nsm_includes_metadata(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        client.lock_pcr(1)
        description = client.describe_nsm()
        assert description["module_id"]
        assert description["pcr_slots"] >= 32
        assert 1 in description["locked_pcrs"]


def test_get_attestation_raw_matches_document(fake_device: str) -> None:
    with NsmClient(device_path=fake_device) as client:
        raw = client.get_attestation_raw(user_data=b"payload")
        assert isinstance(raw, dict)
        assert raw["user_data"] == b"payload"
        doc = client.get_attestation(user_data=b"payload")
        assert doc.module_id == raw["module_id"]
        assert set(doc.locked_pcrs) == set(raw["locked_pcrs"])
