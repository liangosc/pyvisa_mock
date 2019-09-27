from setuptools import setup, find_packages

setup(
    name="pyvisa-mock",
    version="0.1",
    packages=find_packages(),
    python_requires='>=3.6.*',
    install_requires=[
        'pyvisa>=1.9.1',
        'pytest',
        'jupyter'
    ]
)
