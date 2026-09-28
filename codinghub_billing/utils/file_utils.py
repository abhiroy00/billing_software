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
