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

FOLDERS_SCRIPT = """
tell application "Notes"
    set allFolders to folders
    repeat with aFolder in allFolders
        set folderId to id of aFolder
        set folderName to name of aFolder
        set folderContainer to container of aFolder
        if class of folderContainer is folder then
            set folderContainerId to id of folderContainer
        else
            set folderContainerId to ""
        end if
        log "long_id: " & folderId
        log "name: " & folderName
        log "parent: " & folderContainerId
        log "==="
    end repeat
end tell
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
      set noteContainer to container of eachNote
      set noteFolderId to the id of noteContainer
      log "{split}-id: " & noteId & "\n"
      log "{split}-created: " & noteCreated & "\n"
      log "{split}-updated: " & noteUpdated & "\n"
      log "{split}-folder: " & noteFolderId & "\n"
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
@click.option("--schema", is_flag=True, help="Create database schema and exit")
def cli(db_path, stop_after, dump, schema):
    """
    Export Apple Notes to SQLite

    Example usage:

        apple-notes-to-sqlite notes.db

    This will populate notes.db with 'notes' and 'folders' tables containing
    all of your notes.
    """
    if not db_path and not dump:
        raise click.UsageError(
            "Please specify a path to a database file, or use --dump to see the output",
        )
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
        # Create schema
        folder_long_ids_to_id = {}
        if not db["folders"].exists():
            db["folders"].create(
                {
                    "id": int,
                    "long_id": str,
                    "name": str,
                    "parent": int,
                },
                pk="id",
            )
            db["folders"].create_index(["long_id"], unique=True)
            db["folders"].add_foreign_key("parent", "folders", "id")
        if not db["notes"].exists():
            db["notes"].create(
                {
                    "id": str,
                    "created": str,
                    "updated": str,
                    "folder": int,
                    "title": str,
                    "body": str,
                },
                pk="id",
            )
            db["notes"].add_foreign_key("folder", "folders", "id")
        if schema:
            # Our work is done
            return

        for folder in topological_sort(extract_folders()):
            folder["parent"] = folder_long_ids_to_id.get(folder["parent"])
            id = db["folders"].insert(folder, pk="id", replace=True).last_pk
            folder_long_ids_to_id[folder["long_id"]] = id

        expected_count = stop_after
        if not expected_count:
            expected_count = count_notes()

        with click.progressbar(
            length=expected_count, label="Exporting notes", show_eta=True, show_pos=True
        ) as bar:
            for note in extract_notes():
                # Fix the folder
                note["folder"] = folder_long_ids_to_id.get(note["folder"])
                db["notes"].insert(
                    note,
                    replace=True,
                    alter=True,
                )
                bar.update(1)
                i += 1
                if stop_after and i >= stop_after:
                    break


def count_notes():
    return int(
        subprocess.check_output(
            ["osascript", "-e", COUNT_SCRIPT], stderr=subprocess.STDOUT
        )
        .decode("utf8")
        .strip()
    )


def extract_notes():
    split = secrets.token_hex(8)
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
        for key in ("id", "title", "folder", "created", "updated"):
            if line.startswith(f"{split}-{key}: "):
                note[key] = line[len(f"{split}-{key}: ") :]
                found_key = True
                continue
        if not found_key:
            body.append(line)


def extract_folders():
    process = subprocess.Popen(
        ["osascript", "-e", FOLDERS_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    folders = []
    folder = {}
    for line in process.stdout:
        for key in ("long_id", "name", "parent"):
            if line.startswith(f"{key}: ".encode("utf8")):
                folder[key] = line[len(f"{key}: ") :].decode("macroman").strip() or None
                continue
        if line == b"===\n":
            folders.append(folder)
            folder = {}
    return folders


def topological_sort(nodes):
    children = {}
    for node in nodes:
        parent_id = node["parent"]
        if parent_id is not None:
            children.setdefault(parent_id, []).append(node)

    def traverse(node, result):
        result.append(node)
        if node["long_id"] in children:
            for child in children[node["long_id"]]:
                traverse(child, result)

    sorted_data = []
    for node in nodes:
        if node["parent"] is None:
            traverse(node, sorted_data)

    return sorted_data
