"""Logo/signature image handling (Section 43): validate, resize without
distortion, and copy into the app's config directory."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError


def save_uploaded_image(
    source_path: str, dest_dir: Path, dest_filename: str, max_size: tuple[int, int] = (400, 400)
) -> str:
    """Opens, validates, and downsizes an image (preserving aspect ratio),
    saving it as PNG under dest_dir. Raises ValueError on an invalid file."""
    try:
        with Image.open(source_path) as img:
            img = img.convert("RGBA")
            img.thumbnail(max_size, Image.LANCZOS)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / dest_filename
            img.save(dest_path, format="PNG")
            return str(dest_path)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The selected file is not a valid image.") from exc
