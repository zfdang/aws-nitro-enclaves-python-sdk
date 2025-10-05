from setuptools import setup

setup(cffi_modules=["aws_nitro_enclaves/nsm/_cffi_build.py:ffibuilder"])
