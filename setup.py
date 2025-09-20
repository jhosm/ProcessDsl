"""Setup script for BPM DSL."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip() 
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="bpm-dsl",
    version="0.1.0",
    author="BPM DSL Team",
    author_email="team@bpm-dsl.dev",
    description="A text-based domain-specific language for business process modeling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bpm-dsl/bpm-dsl",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "bpm_dsl": ["*.lark"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bpm-dsl=bpm_dsl.cli:cli",
        ],
    },
    keywords="bpm bpmn dsl workflow camunda zeebe business-process",
    project_urls={
        "Bug Reports": "https://github.com/bpm-dsl/bpm-dsl/issues",
        "Source": "https://github.com/bpm-dsl/bpm-dsl",
        "Documentation": "https://bpm-dsl.readthedocs.io/",
    },
)
