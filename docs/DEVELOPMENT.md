Development setup
=================

This project uses a Rust-backed Python extension (PyO3 + maturin). The steps below show a recommended local development workflow.

Quick start (one-liners)

- Create a Python virtualenv and install the editable package with dev extras:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

- Build release wheels (requires Rust toolchain):

```bash
# ensure rustup is installed
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
# build wheels
.venv/bin/maturin build --release -o target/wheels
```

- Install the built wheel into a clean test venv:

```bash
python3 -m venv /tmp/test-venv
source /tmp/test-venv/bin/activate
pip install target/wheels/aws_nitro_enclaves_python_sdk-0.1.0-cp38-abi3-linux_x86_64.whl[dev]
```

Useful Makefile targets

- `make dev` — create `.venv` and install editable package with dev extras.
- `make build-wheel` — build a release wheel with maturin (requires Rust in PATH).
- `make install-wheel` — build then install the wheel into the local venv.
- `make test` — run `pytest` inside the local venv.
- `make clean` — remove venv and build artifacts.

Notes and troubleshooting

- Editable installs may require a virtualenv to exist so that `maturin develop` can detect `VIRTUAL_ENV`.
- Install the Rust toolchain via `rustup` if you see errors about `rustc` or `cargo` missing.
- On CI, ensure you create a virtualenv (or set VIRTUAL_ENV) before running `maturin develop`.
- If you prefer deterministic CI artifacts, use `maturin build` and install the produced wheel(s).

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
  - create and activate a virtualenv before calling `maturin develop`.
  - set $HOME/.cargo/bin in PATH so the Rust toolchain is visible.
  - consider caching pip and cargo registry to speed runs.

If you want, I can add a `pre-commit` configuration and a GitHub Action to run `pre-commit` on PRs.

Addendum: Rust toolchain and matrix wheel builds
-----------------------------------------------

The Makefile includes two helpful targets:

- `make install-rust` — checks whether `rustc` is available and, if not, installs `rustup` non-interactively. After running this target, source your cargo env with:

```bash
source $HOME/.cargo/env
```

- `make build-wheels-matrix` — attempts to build wheels for multiple Python interpreters (python3.8..python3.11). It will skip interpreters that are not present on the machine. Usage:

```bash
# ensure rust is installed and cargo in PATH
make install-rust
source $HOME/.cargo/env
make build-wheels-matrix
# wheels will be placed in target/wheels/
```

These targets are handy for preparing multiple ABI wheels on a machine that has multiple Python interpreters installed (e.g., build worker). For CI reproducibility, consider running builds inside a controlled environment (manylinux docker image) or building on GitHub Actions runners.
