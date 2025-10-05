# AWS Nitro Enclaves Python SDK

A lightweight, secure Python interface for the Nitro Secure Module (NSM) inside AWS Nitro Enclaves.

## Status

**Alpha.** API subject to change while we build out the full feature set.

## Goals

- Provide a stable, high-level `NsmClient` for enclave applications.
- Offer rich error handling and data models for attestation, PCRs, and certificates.
 - Ship pre-built wheels powered by a tiny native shim surfaced through CFFI (see `aws_nitro_enclaves/nsm/_cffi_build.py`).
- Include host-side attestation verification helpers.

## Current capabilities

- Random byte generation via `NsmClient.get_random()`
- PCR inspection and extension helpers (`describe_pcr`, `extend_pcr`, `lock_pcr`, `lock_pcrs`)
- Certificate slot management (`set_certificate`, `describe_certificate`, `remove_certificate`)
- Attestation document creation with optional user data payloads, plus raw dictionary helpers
- NSM metadata inspection via `describe_nsm`

## Getting started

```bash
pip install aws-nitro-enclaves-python-sdk
```

Until the first release lands on PyPI you can install directly from source:

```bash
pip install .
```

## Project layout

- `aws_nitro_enclaves/` – Python package with client, transport, and type definitions.
- `aws_nitro_enclaves/nsm/_cffi_build.py` – CFFI builder containing the native shim used at runtime.
- `tests/` – Python test suite.
- `docs/` – Project documentation (MkDocs).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidance on setting up a development environment and contributing patches.

## License

This project is licensed under the Apache 2.0 License.
