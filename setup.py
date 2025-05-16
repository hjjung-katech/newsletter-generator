#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="newsletter",
    version="0.1.0",
    description="Newsletter generation and testing tools",
    author="Newsletter Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer",
        "rich",
    ],
    entry_points="""
        [console_scripts]
        newsletter=newsletter.cli:app
    """,
)
