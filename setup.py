from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="timefolio-engine",
    version="0.1.0",
    description="Python client library for the Timefolio mock investment contest API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    python_requires=">=3.9",
    packages=find_packages(exclude=["examples", "tests"]),
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        # Install with: pip install timefolio-engine[quant]
        "quant": [
            "python-dotenv>=1.0.1",
            "pykrx>=1.0.48",
            "pandas>=2.0.0",
            "numpy>=1.24.0",
            "scipy>=1.10.0",
            "matplotlib>=3.7.0",
        ],
    },
)
