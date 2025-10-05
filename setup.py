from setuptools import setup

# Ensure compiled cffi extension modules build, and exclude C sources from the wheel.
setup(
	cffi_modules=["aws_nitro_enclaves/nsm/_cffi_build.py:ffibuilder"],
	include_package_data=False,
	package_data={
		"aws_nitro_enclaves.nsm": ["_native.abi3.so"],
	},
	exclude_package_data={
		"aws_nitro_enclaves": ["**/*.c", "**/*.h", "**/*.pyc"],
		"aws_nitro_enclaves.nsm": ["*.c", "*.h", "*_native.cpython-*.so"],
	},
)
