from setuptools import setup, Extension

setup(
    name="data_transfer",
    ext_modules=[
        Extension("data_transfer", 
                  ["data_transfer.c", "spi.c"],
                  libraries=["pthread"],
                  extra_compile_args=['-fPIC'])
    ]
)