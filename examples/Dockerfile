FROM python:3.9-slim

WORKDIR /app

# Install only runtime deps. The wheel we install already contains the compiled
# CFFI extension, so there's no need to install build tools or compile in-image.

RUN apt-get update && \
	apt-get install -y --no-install-recommends ca-certificates libffi8 && \
	rm -rf /var/lib/apt/lists/*

# Copy the pre-built wheel produced by the repository Makefile
COPY examples/wheelhouse /wheelhouse

# Install the wheel (it contains the compiled _native*.so)
RUN python -m pip install --upgrade pip wheel setuptools && python -m pip install /wheelhouse/*.whl

WORKDIR /app
COPY examples/demo_app.py /app/demo_app.py

ENTRYPOINT ["/usr/local/bin/python", "-u", "/app/demo_app.py", "--keep-alive"]
