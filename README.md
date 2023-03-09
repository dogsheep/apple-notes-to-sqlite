# apple-notes-to-sqlite

[![PyPI](https://img.shields.io/pypi/v/apple-notes-to-sqlite.svg)](https://pypi.org/project/apple-notes-to-sqlite/)
[![Changelog](https://img.shields.io/github/v/release/simonw/apple-notes-to-sqlite?include_prereleases&label=changelog)](https://github.com/simonw/apple-notes-to-sqlite/releases)
[![Tests](https://github.com/simonw/apple-notes-to-sqlite/workflows/Test/badge.svg)](https://github.com/simonw/apple-notes-to-sqlite/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/apple-notes-to-sqlite/blob/master/LICENSE)

Export Apple Notes to SQLite

## Installation

Install this tool using `pip`:

    pip install apple-notes-to-sqlite

## Usage

For help, run:

    apple-notes-to-sqlite --help

You can also use:

    python -m apple_notes_to_sqlite --help

To save your notes to a SQLite database called `notes.db` run:

    apple-notes-to-sqlite notes.db

A progress bar will be shown.

You can stop it after a specified number of notes using `--stop-after`:

    apple-notes-to-sqlite notes.db --stop-after 10

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd apple-notes-to-sqlite
    python -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
