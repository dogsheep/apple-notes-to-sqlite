import click
import secrets
import sqlite_utils
import subprocess

COUNT_SCRIPT = """
tell application "Notes"
    set noteCount to count of notes
end tell
log noteCount
"""

EXTRACT_SCRIPT = """
tell application "Notes"
   repeat with eachNote in every note
      set noteId to the id of eachNote
      set noteTitle to the name of eachNote
      set noteBody to the body of eachNote
      set noteCreatedDate to the creation date of eachNote
      set noteCreated to (noteCreatedDate as «class isot» as string)
      set noteUpdatedDate to the modification date of eachNote
      set noteUpdated to (noteUpdatedDate as «class isot» as string)
      log "{split}{split}" & "\n"
      log "{split}-id: " & noteId & "\n"
      log "{split}-created: " & noteCreated & "\n"
      log "{split}-updated: " & noteUpdated & "\n"
      log "{split}-title: " & noteTitle & "\n\n"
      log noteBody & "\n"
   end repeat
end tell
"""


@click.command()
@click.version_option()
@click.argument("db_path")
@click.option("--stop-after", type=int, help="Stop after this many notes")
def cli(db_path, stop_after):
    "Export Apple Notes to SQLite"
    db = sqlite_utils.Database(db_path)
    expected_count = stop_after
    if not expected_count:
        expected_count = count_notes()
    # Use click progressbar
    i = 0
    with click.progressbar(
        length=expected_count, label="Exporting notes", show_eta=True, show_pos=True
    ) as bar:
        for note in extract_notes():
            db["notes"].insert(note, pk="id", replace=True)
            bar.update(1)
            i += 1
            if stop_after and i >= stop_after:
                break


def count_notes():
    # Pass COUNT_SCRIPT to osascript and return standard err
    return int(
        subprocess.check_output(
            ["osascript", "-e", COUNT_SCRIPT], stderr=subprocess.STDOUT
        )
        .decode("utf8")
        .strip()
    )


def extract_notes():
    split = secrets.token_hex(8)
    # Stream stderr output from osascript
    process = subprocess.Popen(
        ["osascript", "-e", EXTRACT_SCRIPT.format(split=split)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Read line by line
    note = {}
    body = []
    for line in process.stdout:
        line = line.decode("mac_roman").strip()
        if line == f"{split}{split}":
            if note.get("id"):
                note["body"] = "\n".join(body)
                yield note
            note = {}
            body = []
        found_key = False
        for key in ("id", "title", "created", "updated"):
            if line.startswith(f"{split}-{key}: "):
                note[key] = line[len(f"{split}-{key}: ") :]
                found_key = True
                continue
        if not found_key:
            body.append(line)
