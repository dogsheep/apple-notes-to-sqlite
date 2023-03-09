from click.testing import CliRunner
from apple_notes_to_sqlite.cli import cli, COUNT_SCRIPT
import sqlite_utils
import json
import os
from unittest.mock import patch

FAKE_OUTPUT = b"""
abcdefg-id: note-1
abcdefg-created: 2023-03-08T16:36:41
abcdefg-updated: 2023-03-08T15:36:41
abcdefg-title: Title 1

This is the content of note 1
abcdefgabcdefg
abcdefg-id: note-2
abcdefg-created: 2023-03-08T16:36:41
abcdefg-updated: 2023-03-08T15:36:41
abcdefg-title: Title 2

This is the content of note 2
abcdefgabcdefg
""".strip()

EXPECTED_NOTES = [
    {
        "id": "note-1",
        "created": "2023-03-08T16:36:41",
        "updated": "2023-03-08T15:36:41",
        "title": "Title 1",
        "body": "This is the content of note 1",
    },
    {
        "id": "note-2",
        "created": "2023-03-08T16:36:41",
        "updated": "2023-03-08T15:36:41",
        "title": "Title 2",
        "body": "This is the content of note 2",
    },
]


@patch("secrets.token_hex")
def test_apple_notes_to_sqlite(mock_token_hex, fp):
    fp.register_subprocess(["osascript", "-e", COUNT_SCRIPT], stdout=b"2")
    fp.register_subprocess(["osascript", "-e", fp.any()], stdout=FAKE_OUTPUT)
    mock_token_hex.return_value = "abcdefg"
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert not os.path.exists("notes.db")
        # Run the CLI
        result = runner.invoke(cli, ["notes.db"])
        assert result.exit_code == 0
        # Check that the database was created
        assert os.path.exists("notes.db")
        db = sqlite_utils.Database("notes.db")
        # Check that the notes table was created
        assert db.table_names() == ["notes"]
        # Check that the notes were inserted
        assert list(db["notes"].rows) == EXPECTED_NOTES


@patch("secrets.token_hex")
def test_apple_notes_to_sqlite_dump(mock_token_hex, fp):
    fp.register_subprocess(["osascript", "-e", COUNT_SCRIPT], stdout=b"2")
    fp.register_subprocess(["osascript", "-e", fp.any()], stdout=FAKE_OUTPUT)
    mock_token_hex.return_value = "abcdefg"
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert not os.path.exists("notes.db")
        result = runner.invoke(cli, ["--dump"])
        # Check the output
        assert result.exit_code == 0
        # Should still be no database
        assert not os.path.exists("notes.db")
        # Output should be newline-delimited JSON
        notes = []
        for line in result.output.splitlines():
            notes.append(json.loads(line))
        assert notes == EXPECTED_NOTES
