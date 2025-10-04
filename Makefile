VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
MATURIN=$(VENV)/bin/maturin

.PHONY: dev build-wheel install-wheel test clean

dev: | $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -e '.[dev]'

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

build-wheel: | $(VENV)
	export PATH="$$HOME/.cargo/bin:$$PATH" && $(MATURIN) build --release -o target/wheels

install-wheel: build-wheel | $(VENV)
	$(PIP) install target/wheels/*.whl[dev]

test: | $(VENV)
	$(PYTHON) -m pytest -q

clean:
	rm -rf $(VENV) target build dist *.egg-info
