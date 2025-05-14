from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Find all packages in the project
packages = find_packages(include=['src', 'src.*', 'config', 'templates'])

setup(
    name="bimigrator",
    version="0.1.0",
    packages=packages + [''],  # Include root package
    package_dir={'': '.'},  # Root directory is the package itself
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "bimigrator=main:main",
        ],
    },
    python_requires=">=3.8",
    package_data={
        '': ['*.yaml', '*.json', '*.hbs', '*.tmdl', '*.md', '*.txt'],
    },
)
