VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: dev build-wheel install-wheel test clean

dev: | $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -e '.[dev]'

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

build-wheel: | $(VENV)
	$(PIP) install --upgrade build
	$(PYTHON) -m build --wheel --outdir dist

install-wheel: build-wheel | $(VENV)
	$(PIP) install dist/*.whl[dev]

test: | $(VENV)
	$(PYTHON) -m pytest -q

clean:
	rm -rf $(VENV) build dist *.egg-info aws_nitro_enclaves_python_sdk.egg-info
