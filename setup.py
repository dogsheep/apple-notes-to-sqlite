from setuptools import setup
import os

VERSION = "0.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="apple-notes-to-sqlite",
    description="Export Apple Notes to SQLite",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/apple-notes-to-sqlite",
    project_urls={
        "Issues": "https://github.com/simonw/apple-notes-to-sqlite/issues",
        "CI": "https://github.com/simonw/apple-notes-to-sqlite/actions",
        "Changelog": "https://github.com/simonw/apple-notes-to-sqlite/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["apple_notes_to_sqlite"],
    entry_points="""
        [console_scripts]
        apple-notes-to-sqlite=apple_notes_to_sqlite.cli:cli
    """,
    install_requires=["click", "sqlite-utils"],
    extras_require={"test": ["pytest", "pytest-subprocess"]},
    python_requires=">=3.7",
)
