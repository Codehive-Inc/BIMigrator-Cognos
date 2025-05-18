from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Get the long description from the README file
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="bimigrator",
    version="0.1.0",
    description="Tool for migrating Tableau workbooks to Power BI TMDL format",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Codehive Inc",
    packages=find_packages(include=['bimigrator', 'bimigrator.*']),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "bimigrator=bimigrator.main:main",
        ],
    },
    python_requires=">=3.10",
    package_data={
        'bimigrator': [
            '*.yaml',
            '*.json',
            '*.md',
            '*.txt',
            'templates/*',
            'config/*'
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
