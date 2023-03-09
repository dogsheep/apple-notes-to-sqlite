from click.testing import CliRunner
from apple_notes_to_sqlite.cli import cli, COUNT_SCRIPT, FOLDERS_SCRIPT
import sqlite_utils
import json
import os
from unittest.mock import patch

FOLDER_OUTPUT = b"""
long_id: folder-1
name: Folder 1
parent: 
===
long_id: folder-2
name: Folder 2
parent: folder-1
===
"""

FAKE_OUTPUT = b"""
abcdefg-id: note-1
abcdefg-created: 2023-03-08T16:36:41
abcdefg-updated: 2023-03-08T15:36:41
abcdefg-folder: folder-1
abcdefg-title: Title 1

This is the content of note 1
abcdefgabcdefg
abcdefg-id: note-2
abcdefg-created: 2023-03-08T16:36:41
abcdefg-updated: 2023-03-08T15:36:41
abcdefg-folder: folder-2
abcdefg-title: Title 2

This is the content of note 2
abcdefgabcdefg
""".strip()

EXPECTED_NOTES = [
    {
        "id": "note-1",
        "created": "2023-03-08T16:36:41",
        "updated": "2023-03-08T15:36:41",
        "folder": 1,
        "title": "Title 1",
        "body": "This is the content of note 1",
    },
    {
        "id": "note-2",
        "created": "2023-03-08T16:36:41",
        "updated": "2023-03-08T15:36:41",
        "folder": 2,
        "title": "Title 2",
        "body": "This is the content of note 2",
    },
]
EXPECTED_DUMP_NOTES = [
    dict(note, folder=f"folder-{note['folder']}") for note in EXPECTED_NOTES
]


@patch("secrets.token_hex")
def test_apple_notes_to_sqlite(mock_token_hex, fp):
    fp.register_subprocess(["osascript", "-e", COUNT_SCRIPT], stdout=b"2")
    fp.register_subprocess(["osascript", "-e", FOLDERS_SCRIPT], stdout=FOLDER_OUTPUT)
    fp.register_subprocess(["osascript", "-e", fp.any()], stdout=FAKE_OUTPUT)
    mock_token_hex.return_value = "abcdefg"
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert not os.path.exists("notes.db")
        result = runner.invoke(cli, ["notes.db"])
        assert result.exit_code == 0
        # Check that the database was created
        assert os.path.exists("notes.db")
        db = sqlite_utils.Database("notes.db")
        # Check tables were created
        assert set(db.table_names()) == {"notes", "folders"}
        # Check that the notes were inserted
        assert list(db["notes"].rows) == EXPECTED_NOTES


@patch("secrets.token_hex")
def test_apple_notes_to_sqlite_dump(mock_token_hex, fp):
    fp.register_subprocess(["osascript", "-e", COUNT_SCRIPT], stdout=b"2")
    fp.register_subprocess(["osascript", "-e", FOLDERS_SCRIPT], stdout=FOLDER_OUTPUT)
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
        assert notes == EXPECTED_DUMP_NOTES


@patch("secrets.token_hex")
def test_folders(mock_token_hex, fp):
    fp.register_subprocess(["osascript", "-e", COUNT_SCRIPT], stdout=b"2")
    fp.register_subprocess(["osascript", "-e", FOLDERS_SCRIPT], stdout=FOLDER_OUTPUT)
    fp.register_subprocess(["osascript", "-e", fp.any()], stdout=FAKE_OUTPUT)
    mock_token_hex.return_value = "abcdefg"
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert not os.path.exists("folders.db")
        result = runner.invoke(cli, ["folders.db"])
        assert result.exit_code == 0
        assert os.path.exists("folders.db")
        db = sqlite_utils.Database("folders.db")
        assert db["folders"].schema == (
            "CREATE TABLE [folders] (\n"
            "   [id] INTEGER PRIMARY KEY,\n"
            "   [long_id] TEXT,\n"
            "   [name] TEXT,\n"
            "   [parent] INTEGER,\n"
            "   FOREIGN KEY([parent]) REFERENCES [folders]([id])\n"
            ")"
        )
        assert list(db["folders"].rows) == [
            {"id": 1, "long_id": "folder-1", "name": "Folder 1", "parent": None},
            {"id": 2, "long_id": "folder-2", "name": "Folder 2", "parent": 1},
        ]
