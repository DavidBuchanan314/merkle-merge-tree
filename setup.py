"""
Setup script for exclusion-tlog package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="exclusion-tlog",
    version="0.1.0",
    author="David Buchanan",
    description="A novel transparency log with exclusion proofs based on sorted merkle trees",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DavidBuchanan314/exclusion-tlog",
    py_modules=["exclusion_tlog"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest",
            "black",
            "mypy",
        ],
    },
)
