import click
import json
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
      log "{split}-id: " & noteId & "\n"
      log "{split}-created: " & noteCreated & "\n"
      log "{split}-updated: " & noteUpdated & "\n"
      log "{split}-title: " & noteTitle & "\n\n"
      log noteBody & "\n"
      log "{split}{split}" & "\n"
   end repeat
end tell
""".strip()


@click.command()
@click.version_option()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=False,
)
@click.option("--stop-after", type=int, help="Stop after this many notes")
@click.option("--dump", is_flag=True, help="Output notes to standard output")
def cli(db_path, stop_after, dump):
    "Export Apple Notes to SQLite"
    if not db_path and not dump:
        raise click.UsageError(
            "Please specify a path to a database file, or use --dump to see the output",
        )
    expected_count = stop_after
    if not expected_count:
        expected_count = count_notes()
    # Use click progressbar
    i = 0
    if dump:
        for note in extract_notes():
            click.echo(json.dumps(note))
            i += 1
            if stop_after and i >= stop_after:
                break
    else:
        db = sqlite_utils.Database(db_path)
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
                note["body"] = "\n".join(body).strip()
                yield note
            note = {}
            body = []
            continue
        found_key = False
        for key in ("id", "title", "created", "updated"):
            if line.startswith(f"{split}-{key}: "):
                note[key] = line[len(f"{split}-{key}: ") :]
                found_key = True
                continue
        if not found_key:
            body.append(line)
