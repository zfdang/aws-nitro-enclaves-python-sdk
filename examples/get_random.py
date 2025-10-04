"""Demonstrates fetching random bytes from the NSM."""

from __future__ import annotations

from aws_nitro_enclaves.nsm import NsmClient


def main() -> None:
    with NsmClient() as client:
        data = client.get_random(32)
        print(f"Random bytes: {data.hex()}")

        pcr0 = client.describe_pcr(0)
        print(f"PCR[0]: {pcr0.digest.hex()}")

        attestation = client.get_attestation(user_data=b"demo")
        print(f"Attestation module id: {attestation.module_id}")


if __name__ == "__main__":
    main()
