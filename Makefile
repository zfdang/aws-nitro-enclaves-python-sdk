VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
MATURIN=$(VENV)/bin/maturin

.PHONY: dev build-wheel install-wheel test clean install-rust build-wheels-matrix

dev: | $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -e '.[dev]'

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install maturin

build-wheel: | $(VENV)
	export PATH="$$HOME/.cargo/bin:$$PATH" && $(MATURIN) build --release -o target/wheels

install-rust:
	@command -v rustc >/dev/null 2>&1 || (echo "rustc not found, installing rustup..." && \
	 curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
	 echo "To use Rust in this shell run: source $$HOME/.cargo/env")


PYTHON_MATRIX=python3.8 python3.9 python3.10 python3.11

build-wheels-matrix: | $(VENV) install-rust
	@mkdir -p target/wheels
	@for PY in $(PYTHON_MATRIX); do \
	 if command -v $$PY >/dev/null 2>&1; then \
	  echo "Building wheel for $$PY"; PATH="$$HOME/.cargo/bin:$$PATH" $(MATURIN) build --release -o target/wheels --interpreter="$$PY"; \
	 else \
	  echo "Skipping $$PY (interpreter not found)"; \
	 fi; \
	done

install-wheel: build-wheel | $(VENV)
	$(PIP) install target/wheels/*.whl[dev]

test: | $(VENV)
	$(PYTHON) -m pytest -q

clean:
	rm -rf $(VENV) target build dist *.egg-info
