"""Database backup & restore (Section 27): timestamped SQLite copies.

Pure file logic — dicts/paths in, dicts out — so it is unit-testable
without a display. The controller layer wires in the live DB path,
the backup folder from settings and engine disposal.

Restore safety: the live database is always safety-copied into the
backup folder (``pre_restore_*``) before being replaced, and the
caller must dispose the SQLAlchemy engine afterwards so pooled
connections don't keep pointing at the old file.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"
BACKUP_PREFIX = "codinghub_backup_"
PRE_RESTORE_PREFIX = "pre_restore_"


class BackupError(Exception):
    pass


def backup_filename(when: datetime | None = None) -> str:
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{BACKUP_PREFIX}{stamp}.db"


def format_file_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def _backup_file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "size_display": format_file_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "modified_display": datetime.fromtimestamp(stat.st_mtime).strftime("%d-%m-%Y %H:%M"),
    }


def list_backups(backup_dir: str | Path) -> list[dict]:
    folder = Path(backup_dir)
    if not folder.is_dir():
        return []
    files = sorted(
        (p for p in folder.glob("*.db") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [_backup_file_info(p) for p in files]


def create_backup(db_path: str | Path, backup_dir: str | Path) -> dict:
    source = Path(db_path)
    if not source.is_file():
        raise BackupError("Database file not found — koi data save nahi hua abhi tak.")
    folder = Path(backup_dir)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise BackupError("Backup folder create nahi ho paya. Dusri location chuno.") from exc

    dest = folder / backup_filename()
    counter = 1
    while dest.exists():
        # Same-second double backup — name collide na ho.
        dest = folder / backup_filename().replace(".db", f"_{counter}.db")
        counter += 1
    try:
        shutil.copy2(source, dest)
    except Exception as exc:
        raise BackupError("Backup copy fail ho gaya. Disk space / permission check karo.") from exc
    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise BackupError("Backup file khaali bana — backup nahi liya gaya.")
    return _backup_file_info(dest)


def validate_backup_file(path: str | Path) -> None:
    candidate = Path(path)
    if not candidate.is_file():
        raise BackupError("Ye backup file mili nahi.")
    if candidate.suffix.lower() not in (".db", ".sqlite", ".sqlite3"):
        raise BackupError("Sirf .db backup file restore ho sakti hai.")
    try:
        with open(candidate, "rb") as fh:
            header = fh.read(len(SQLITE_MAGIC))
    except OSError as exc:
        raise BackupError("Backup file padhi nahi ja saki.") from exc
    if header != SQLITE_MAGIC:
        raise BackupError("Ye valid database backup nahi lag rahi (header mismatch).")


def verify_database_tables(db_path: str | Path, required_tables: tuple[str, ...] = ("users",)) -> None:
    """Restored file khul rahi hai aur expected tables hain — bina ORM ke check."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise BackupError("Restored database khul nahi rahi — purani safety copy se wapas karo.") from exc
    tables = {r[0] for r in rows}
    missing = [t for t in required_tables if t not in tables]
    if missing:
        raise BackupError("Ye file CodingHub ka database nahi lag rahi (tables missing).")


def delete_backup(path: str | Path, backup_dir: str | Path) -> None:
    candidate = Path(path)
    folder = Path(backup_dir)
    try:
        # Path traversal guard — backup folder ke bahar delete kabhi nahi.
        candidate.resolve().relative_to(folder.resolve())
    except Exception as exc:
        raise BackupError("Ye file backup folder ke andar nahi hai.") from exc
    if not candidate.is_file():
        raise BackupError("Ye backup file mili nahi (pehle hi delete ho gayi?).")
    try:
        candidate.unlink()
    except OSError as exc:
        raise BackupError("Backup file delete nahi ho payi.") from exc


def restore_backup(backup_path: str | Path, db_path: str | Path, backup_dir: str | Path) -> dict:
    """Live DB ko safety-copy karke backup file se replace karta hai.

    Returns {"safety_copy": {...}} — caller engine dispose + verify kare.
    """
    candidate = Path(backup_path)
    validate_backup_file(candidate)

    live = Path(db_path)
    folder = Path(backup_dir)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise BackupError("Backup folder ready nahi ho paya.") from exc

    safety: dict | None = None
    if live.is_file():
        dest = folder / f"{PRE_RESTORE_PREFIX}{datetime.now():%Y%m%d_%H%M%S}.db"
        try:
            shutil.copy2(live, dest)
            safety = _backup_file_info(dest)
        except Exception as exc:
            raise BackupError("Safety copy nahi ban payi — restore rok diya (data safe hai).") from exc

    try:
        shutil.copy2(candidate, live)
    except Exception as exc:
        raise BackupError("Restore copy fail ho gaya — app restart mat karo, help lo.") from exc
    return {"safety_copy": safety}
