Development setup
=================

This project uses a small native shim surfaced through CFFI. The steps below show a recommended local development workflow for the Python + CFFI build.

Quick start (one-liners)

- Create a Python virtualenv and install the editable package with dev extras:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

This project no longer requires Rust. For local editable installs and testing, use a Python virtualenv and pip:

```bash
# create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate
# install the package in editable mode with development extras
pip install -e .[dev]
```

- Install the built wheel into a clean test venv:

```bash
python3 -m venv /tmp/test-venv
source /tmp/test-venv/bin/activate
pip install target/wheels/aws_nitro_enclaves_python_sdk-0.1.0-cp38-abi3-linux_x86_64.whl[dev]
```

Useful Makefile targets

- `make dev` — create `.venv` and install editable package with dev extras.
`make test` — run `pytest` inside the local venv.
- `make test` — run `pytest` inside the local venv.
- `make clean` — remove venv and build artifacts.

Notes and troubleshooting

Notes and troubleshooting

- Editable installs require a virtualenv to exist so that build hooks detect the environment.
- On CI, create and activate a virtualenv before installing the package in editable mode.



Running the example

```bash
# use the local dev venv
source .venv/bin/activate
# for example run, create a fake socket for local dev
touch /tmp/nsm.sock
python -c "from aws_nitro_enclaves.nsm import NsmClient; print(NsmClient(device_path='/tmp/nsm.sock').get_random(16))"
```

CI hints

- The included `.github/workflows/ci-lite.yml` demonstrates a minimal pipeline. Key items:
  - create and activate a virtualenv before installing the package.
  - consider caching pip to speed runs.

If you want, I can add a `pre-commit` configuration and a GitHub Action to run `pre-commit` on PRs.

Addendum: matrix testing and reproducible CI builds
--------------------------------------------------

If you need to test on multiple Python interpreters in a single runner, install the interpreters on the machine and run the Makefile targets that create separate venvs per interpreter. For reproducible wheel builds in CI, prefer building inside a manylinux docker image and publishing finalized wheels from a controlled build worker.
