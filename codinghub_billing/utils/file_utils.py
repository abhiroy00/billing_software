"""Generic file attachment handling (Section 16: expense attachments)."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path


def save_attachment(source_path: str, dest_dir: Path) -> str:
    """Copies source_path into dest_dir under a collision-proof filename,
    preserving the original extension. Returns the new path as a string."""
    source = Path(source_path)
    if not source.is_file():
        raise ValueError("The selected file could not be found.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{uuid.uuid4().hex}{source.suffix}"
    dest_path = dest_dir / dest_name
    shutil.copy2(source, dest_path)
    return str(dest_path)


def save_import_file(source_path: str, dest_dir: Path) -> str:
    """Saves a copy of an imported Excel/CSV file for record-keeping.

    Keeps the original filename (prefixed with a short id to avoid
    collisions) so the user can recognise/delete it later.
    Returns the new path as a string."""
    from datetime import datetime

    source = Path(source_path)
    if not source.is_file():
        raise ValueError("The selected file could not be found.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in source.name)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_name = f"{stamp}_{uuid.uuid4().hex[:6]}_{safe_name}"
    dest_path = dest_dir / dest_name
    shutil.copy2(source, dest_path)
    return str(dest_path)


def delete_file_safe(path: str | Path | None) -> bool:
    """Deletes a previously saved file. Never raises — returns True when
    a file was actually removed, False otherwise (missing/empty path)."""
    if not path:
        return False
    try:
        target = Path(path)
        if target.is_file():
            target.unlink()
            return True
    except Exception:
        pass
    return False
