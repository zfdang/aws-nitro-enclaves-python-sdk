Demo app for NSM SDK
====================

This example builds a small Docker image that contains the Python package and a demo script which:

- Calls `get_random(32)` and logs the result (hex)
- Calls `get_attestation()` and logs the resulting payload (JSON-ish)

Building and running
---------------------

This demo is intended to be run as an enclave via `nitro-cli` in debug mode. On a host with Nitro Enclaves installed, do the following from the `examples/` directory.

1. Build the Docker image (from repo root):

```bash
# from repository root
docker build -f examples/Dockerfile -t nsm-demo:latest .
```

2. Create an enclave image (EIF) with `nitro-cli`:

```bash
nitro-cli build-enclave --docker-uri nsm-demo:latest --output-file demo.eif
```

3. Run the enclave in debug mode and fetch logs (example):

```bash
# Run enclave (example with 256MB memory, 2 vCPUs)
nitro-cli run-enclave --eif-path demo.eif --enclave-cid 16 --memory 256 --cpu-count 2 --debug-mode

# Find the PID and fetch the console logs; nitro-cli prints the console log file location which you can tail
nitro-cli console --enclave-id <ENCLAVE_ID>
```

Notes
-----
- If you do not have a physical NSM device available on the host, the demo will fail opening `/var/run/nsm`.
  For development or CI you can run the demo in a container with a mock transport or use the `transport_factory` override in code.
- The Dockerfile installs the package inside the image. The demo expects the package to be importable as `aws_nitro_enclaves`.
