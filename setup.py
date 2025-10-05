from setuptools import setup

# Ensure compiled cffi extension modules and any .so files are included in
# the built wheel. setuptools will include package data listed here.
setup(
	cffi_modules=["aws_nitro_enclaves/nsm/_cffi_build.py:ffibuilder"],
	include_package_data=True,
	package_data={
		# include any compiled shared objects under the package
		"aws_nitro_enclaves": ["**/*.so", "**/*.abi3.so"],
	},
)
