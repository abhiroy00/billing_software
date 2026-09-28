import sqlite3

import pytest

from services import backup_service


def _make_db(path, marker: str = "live") -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users (name) VALUES (?)", (marker,))
        conn.commit()
    finally:
        conn.close()


def _read_marker(path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT name FROM users").fetchone()[0]
    finally:
        conn.close()


def test_create_and_list_backup(tmp_path):
    db = tmp_path / "codinghub.db"
    _make_db(db)
    backup_dir = tmp_path / "backups"

    info = backup_service.create_backup(db, backup_dir)

    assert info["name"].startswith("codinghub_backup_")
    assert info["name"].endswith(".db")
    assert info["size_bytes"] > 0
    assert info["modified_display"]

    rows = backup_service.list_backups(backup_dir)
    assert len(rows) == 1
    assert rows[0]["name"] == info["name"]
    # Backup me wahi data jo live DB me tha.
    assert _read_marker(rows[0]["path"]) == "live"


def test_list_backups_empty_when_missing(tmp_path):
    assert backup_service.list_backups(tmp_path / "nope") == []


def test_create_backup_missing_db_raises(tmp_path):
    with pytest.raises(backup_service.BackupError, match="not found"):
        backup_service.create_backup(tmp_path / "missing.db", tmp_path / "backups")


def test_restore_replaces_db_and_keeps_safety_copy(tmp_path):
    live = tmp_path / "codinghub.db"
    _make_db(live, marker="live")
    backup_dir = tmp_path / "backups"

    info = backup_service.create_backup(live, backup_dir)

    # Live data badal gaya, phir restore — purana data wapas aana chahiye.
    _make_db(str(live) + ".new", marker="newer")
    import shutil

    shutil.copy2(str(live) + ".new", live)
    assert _read_marker(live) == "newer"

    result = backup_service.restore_backup(info["path"], live, backup_dir)

    assert _read_marker(live) == "live"
    assert result["safety_copy"] is not None
    assert result["safety_copy"]["name"].startswith("pre_restore_")
    assert _read_marker(result["safety_copy"]["path"]) == "newer"


def test_restore_rejects_non_database_file(tmp_path):
    bad = tmp_path / "fake.db"
    bad.write_text("ye database nahi hai")
    live = tmp_path / "codinghub.db"
    _make_db(live)

    with pytest.raises(backup_service.BackupError, match="valid database backup"):
        backup_service.restore_backup(bad, live, tmp_path / "backups")
    # Live DB untouched.
    assert _read_marker(live) == "live"


def test_restore_rejects_wrong_extension(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    live = tmp_path / "codinghub.db"
    _make_db(live)

    with pytest.raises(backup_service.BackupError, match=".db"):
        backup_service.restore_backup(bad, live, tmp_path / "backups")


def test_verify_tables_rejects_foreign_db(tmp_path):
    other = tmp_path / "other.db"
    conn = sqlite3.connect(other)
    try:
        conn.execute("CREATE TABLE something_else (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(backup_service.BackupError, match="tables missing"):
        backup_service.verify_database_tables(other)


def test_delete_backup(tmp_path):
    db = tmp_path / "codinghub.db"
    _make_db(db)
    backup_dir = tmp_path / "backups"
    info = backup_service.create_backup(db, backup_dir)

    backup_service.delete_backup(info["path"], backup_dir)
    assert backup_service.list_backups(backup_dir) == []

    with pytest.raises(backup_service.BackupError, match="mili nahi"):
        backup_service.delete_backup(info["path"], backup_dir)


def test_delete_backup_blocks_path_traversal(tmp_path):
    outside = tmp_path / "outside.db"
    _make_db(outside)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    with pytest.raises(backup_service.BackupError, match="andar nahi"):
        backup_service.delete_backup(outside, backup_dir)
    assert outside.is_file()


def test_format_file_size():
    assert backup_service.format_file_size(500) == "500 B"
    assert backup_service.format_file_size(2048) == "2.0 KB"
    assert backup_service.format_file_size(5 * 1024 * 1024) == "5.0 MB"
