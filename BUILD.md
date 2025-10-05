BUILD and packaging guide
=========================

This document contains step-by-step instructions to build the project (including precompiling the CFFI native shim), create sdist and wheel packages, and the common troubleshooting tips encountered when building or running the demo (Docker image, EIF, and running enclaves).

Prerequisites
-------------

On Debian/Ubuntu hosts you likely need:

  sudo apt-get update
  sudo apt-get install -y build-essential python3-dev libffi-dev pkg-config 

Python tooling (recommended inside a venv):

  rm -fr .venv
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install build wheel setuptools cffi

Quick build steps (local, reproducible)
---------------------------------------

1) Precompile CFFI extension (creates compiled shared object)

  This project ships a CFFI builder at `aws_nitro_enclaves/nsm/_cffi_build.py` which:
  - generates the `_native` CFFI wrapper;
  - compiles the stable C implementation at `aws_nitro_enclaves/nsm/_shim.c`;
  - links them into a single `_native.abi3.so` shared library.

   Run:

     python -m aws_nitro_enclaves.nsm._cffi_build

  Expectation: file `aws_nitro_enclaves/nsm/_native.abi3.so` should appear in `aws_nitro_enclaves/nsm/`.

2) Build sdist + wheel using PEP 517/518 toolchain

   Run:

     python -m build

  Output: artifacts in `dist/` (for example, `aws_nitro_enclaves_python_sdk-1.0.0-cp39-cp39-linux_x86_64.whl` and a `tar.gz` sdist). The wheel is platform-specific because it contains a compiled extension.

   Checks:

     ls -l dist/
     # the wheel should include exactly one shared object (abi3) and no C sources
     unzip -l dist/*.whl | grep 'aws_nitro_enclaves/nsm/_native.*\.so' || true
     unzip -l dist/*.whl | grep -E 'aws_nitro_enclaves/nsm/\.(c|h)$' || true
     tar -xOzf dist/*.tar.gz PKG-INFO | sed -n '1,120p'

   Wheel hygiene (single shared object): this repo is configured so the wheel ships only `_native.abi3.so` and excludes C sources. If you ever see an interpreter-specific file like `_native.cpython-*.so` produced locally, remove it before building the wheel (the packaging rules already exclude it, but keeping the tree clean helps):

     rm -f aws_nitro_enclaves/nsm/_native.cpython-*.so

One-shot verification (Makefile)
--------------------------------

Use the Makefile’s verify target to run an end-to-end check in one command. It will:
- prebuild the CFFI extension;
- build the wheel;
- verify the wheel contains exactly one `_native.abi3.so` and no `*.c`/`*.h` sources;
- import the native module to ensure `ffi`/`lib` are present;
- run the test suite.

Run:

```bash
make verify
```

3) Docker demo image / EIF / Enclave run (project provides Makefile targets)

   The `examples/Dockerfile` expects a prebuilt wheel in `examples/wheelhouse/` by default in this repo's flow. The Makefile orchestrates the steps: build wheel, copy to wheelhouse, build docker image, build EIF, and run enclave. Example one-liner (Makefile provides this):

     make demo-run

   Or run sub-steps manually if you prefer:

     # build wheel and copy to examples/wheelhouse
     python -m build
     mkdir -p examples/wheelhouse
     cp dist/*.whl examples/wheelhouse/

     # build docker image (example tag: nsm-demo:latest)
     docker build -f examples/Dockerfile -t nsm-demo:latest .

     # build EIF from the docker image (requires nitro-cli on host)
     sudo nitro-cli build-enclave --docker-uri nsm-demo:latest --output-file demo.eif

     # run enclave (adjust memory/cpu as necessary)
     sudo nitro-cli run-enclave --eif-path demo.eif --memory 1024 --cpu-count 2 --attach-console

Troubleshooting notes (collected from development)
-------------------------------------------------

1) Missing compiled .so in installed wheel

Symptoms:

- Import errors or runtime AttributeError complaining about missing `_native` attributes or module.

Causes:

- Building from a source tree without running the CFFI builder can miss the shared object in some flows.
- Installing an outdated wheel into the environment.

Fixes:

- Run `python -m aws_nitro_enclaves.nsm._cffi_build` before `python -m build` to ensure `_native.abi3.so` exists and is picked up.
- Rebuild and reinstall the latest wheel.

2) Enclave run fails with E29/E39 Ioctl / process connection errors

Symptoms:

- `nitro-cli run-enclave` prints E29/E39 errors and references `/var/log/nitro_enclaves/err*.log`.
- Error logs show messages like "Create VM ioctl failed", "Insufficient CPUs available (requested X, but maximum is 0)", or "At least N MB must be allocated (which is 4 times the EIF file size)".

Causes and fixes:

- Another enclave is already running and has taken the CPU pool or required resources. Use `nitro-cli describe-enclaves` and `nitro-cli terminate-enclave --enclave-id <id>` to stop it before starting another.

- The host allocator configuration (`/etc/nitro_enclaves/allocator.yaml`) limits the CPU pool or memory available to enclaves. Edit this file to increase `cpu_count` or provide a `cpu_pool` that includes usable host CPUs, and increase `memory_mib` or hugepage settings as required; then restart the Nitro Enclaves allocator service.

- Hugepages/host memory: verify hugepages are available for the requested EIF size. Inspect `/proc/meminfo` (HugePages_Total, Hugepagesize) and adjust the allocator or host sysctl if necessary.

- Unexpected EIF minimum size checks: the enclave manager applies several heuristics for required sizes; if logs show "At least X MB must be allocated (which is 4 times the EIF file size)", consider increasing the `memory_mib` passed to `nitro-cli run-enclave` (or update allocator config) until the allocation succeeds.

3) Demo inside the enclave cannot open NSM device (NsmDeviceNotFoundError)

Symptoms:

- Python inside enclave raises NsmDeviceNotFoundError complaining that `/var/run/nsm` or `/dev/nsm` doesn't exist.

Cause:

- Host NSM device or socket not provided inside the enclave image or the path used by the SDK doesn't match the host's exported device path.

Fixes/Workarounds:

- Confirm where the host exposes NSM (e.g., `/dev/nsm` or `/var/run/nsm`) and mount or expose that path into the Docker image or enclave environment so it exists at the expected path. If you use `nitro-cli` and the host provides a device via some resource manager, ensure it's available in the running enclave.

- The SDK default device path can be customized when creating `NsmClient(device_path="/dev/nsm")` or by changing `DEFAULT_DEVICE_PATH` in the transport implementation. Prefer passing `device_path` explicitly to `NsmClient` for portability.

4) Wheel missing compiled .so when installed in container

Symptoms:

- Locally wheel contains `_native.abi3.so`, but after `pip install` inside the Docker container the installed package lacks the shared library (causing runtime errors).

Cause:

- The wheel being installed is not the freshly built one (cache or wrong wheelhouse path).

Fix:

- Rebuild the wheel, copy to `examples/wheelhouse` and rebuild the Docker image with `--no-cache`:

    python -m build
    mkdir -p examples/wheelhouse
    cp dist/*.whl examples/wheelhouse/
    docker build --no-cache -f examples/Dockerfile -t nsm-demo:latest .

5) Build environment errors / CFFI compilation fails

Symptoms:

- CFFI compile step fails with errors referencing missing libffi headers or failing C compile.

Fixes:

- On Debian/Ubuntu install `libffi-dev`, `build-essential`, and `python3-dev`. On RHEL/CentOS install corresponding `libffi-devel` and development toolchain.
- The CFFI builder compiles against `aws_nitro_enclaves/nsm/_shim.c`. Ensure this file exists and your compiler can find standard headers.
- If needed, pre-compile locally and verify `_native.abi3.so` appears before packaging.

6) PKG-INFO and license metadata

Notes:

- `PKG-INFO` is generated during sdist/wheel build and is populated from your project metadata (`pyproject.toml` or setup.py). If you change `pyproject.toml` (e.g., license), re-run `python -m build` to produce updated PKG-INFO.

- `SOURCES.txt` is generated for sdist and lists files included in the source distribution. Its contents are controlled by package discovery and `MANIFEST.in` (if present) plus defaults. Add a `MANIFEST.in` if you need fine-grained control over what goes into the sdist.

Useful debug commands
---------------------

# show built artifacts
ls -l dist/

# inspect wheel contents (ensure only abi3 .so is present, no C sources)
unzip -l dist/*.whl | grep 'aws_nitro_enclaves/nsm/_native.*\.so' || true
unzip -l dist/*.whl | grep -E 'aws_nitro_enclaves/nsm/\.(c|h)$' || true

# inspect sdist PKG-INFO
tar -xOzf dist/*.tar.gz PKG-INFO | sed -n '1,200p'

# inspect nitro enclave error logs mentioned by nitro-cli
sudo ls -l /var/log/nitro_enclaves/
sudo tail -n 200 /var/log/nitro_enclaves/err*.log

# check nitro allocator config
sudo cat /etc/nitro_enclaves/allocator.yaml

# check host hugepages
grep -i huge /proc/meminfo

# list current enclaves
sudo nitro-cli describe-enclaves

# terminate an enclave
sudo nitro-cli terminate-enclave --enclave-id <id>

Appendix: Example quick commands to build and validate (copy/paste)
----------------------------------------------------------------

```bash
cd /path/to/repo
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install build wheel setuptools cffi
python -m aws_nitro_enclaves.nsm._cffi_build
python -m build
ls -l dist/
WHEEL=$(ls -1 dist/*.whl | head -n1)
unzip -l "$WHEEL" | grep _native || true
```


If you'd like, I can also:
- Commit this `BUILD.md` into the repo (done automatically by me if you want),
- Run a build in this environment and paste the logs (if you want me to run it here), or
- Create a minimal `MANIFEST.in` for you to control sdist content.

