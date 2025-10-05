IMAGE_NAME := nsm-demo:latest
EIF_FILE := demo.eif
ENCLAVE_ID := 
MEMORY := 1024
VCPU := 2

.PHONY: help demo-build demo-eif demo-run demo-console

help:
	@echo "Makefile targets:"
	@echo "  make demo-build   # build the Docker image for the demo"
	@echo "  make demo-eif     # build an EIF from the demo image using nitro-cli"
	@echo "  make demo-run     # run the EIF in debug mode (prints nitro-cli command)"
	@echo "  make demo-console # attach to the enclave console (requires ENCLAVE_ID env)"

# demo-build will produce a wheel that already contains the compiled CFFI .so
# so the Docker image can install the wheel without compiling inside the image.
demo-build:
	rm -rf examples/wheelhouse
	mkdir -p examples/wheelhouse
	# Build a wheel that includes the compiled CFFI extension
	$(MAKE) build-wheel-compiled
	cp -v dist/*.whl examples/wheelhouse/ || true
	# verify wheel exists
	@if [ -z "$$(ls -A examples/wheelhouse 2>/dev/null)" ]; then \
		echo "No wheel found in examples/wheelhouse — aborting"; exit 1; \
	fi
	docker build -f examples/Dockerfile -t $(IMAGE_NAME) .

demo-eif: demo-build
	nitro-cli build-enclave --docker-uri $(IMAGE_NAME) --output-file $(EIF_FILE)

demo-run: demo-eif
	@echo "Running enclave in debug mode (this will block). Use Ctrl-C to stop."
	nitro-cli run-enclave --eif-path $(EIF_FILE) --enclave-cid 16 --memory $(MEMORY) --cpu-count $(VCPU) --debug-mode

demo-console:
	@if [ -z "$(ENCLAVE_ID)" ]; then \
		echo "Set ENCLAVE_ID env var, e.g. ENCLAVE_ID=$$(nitro-cli describe-enclaves | jq -r '.[0].EnclaveID') make demo-console"; exit 1; fi
	nitro-cli console --enclave-id $(ENCLAVE_ID)
VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: dev build-wheel build-wheel-compiled install-wheel test clean

dev: | $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -e '.[dev]'

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

build-wheel: | $(VENV)
	$(PIP) install --upgrade build
	$(PYTHON) -m build --wheel --outdir dist

# Build a wheel which includes the compiled CFFI artifacts (.so). This runs the
# project's CFFI build script to generate the shared object and then builds a wheel
# that will include it. Use this for producing wheels distributed to environments
# (so they don't need to compile in their runtime image).
build-wheel-compiled: | $(VENV)
	$(PIP) install --upgrade build cffi wheel setuptools
	# Pre-compile cffi extension into the source tree. Run as a module to avoid
	# sys.path issues where package-local filenames shadow stdlib modules.
	$(PYTHON) -m aws_nitro_enclaves.nsm._cffi_build
	# Build the wheel; the compiled _native*.so should be picked up and included
	$(PYTHON) -m build --wheel --outdir dist

install-wheel: build-wheel | $(VENV)
	$(PIP) install dist/*.whl[dev]

test: | $(VENV)
	$(PYTHON) -m pytest -q

clean:
	rm -rf $(VENV) build dist examples/wheelhouse *.egg-info aws_nitro_enclaves_python_sdk.egg-info
