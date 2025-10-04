# Contributing

Thank you for taking the time to improve the AWS Nitro Enclaves Python SDK!

## Development environment

1. Install Python 3.8 or newer.
2. Install Rust (stable toolchain) and [maturin](https://github.com/PyO3/maturin).
3. Create a virtual environment and install development dependencies:
   ```bash
   pip install -e .[dev]
   ```
4. Run the test suite:
   ```bash
   maturin develop
   pytest
   ```

## Coding standards

- Keep public APIs type-annotated and documented.
- Run `ruff` and `mypy` before opening a pull request.
- Include unit tests alongside bug fixes and new features.

## Commit messages

Follow the conventional commits style when possible (`feat:`, `fix:`, `docs:`, etc.).

We welcome issues and pull requests—thanks for helping us build a great SDK!
