"""Filesystem storage helper for generated image and video artifacts."""

from __future__ import annotations

import base64
import shutil
from pathlib import Path
from uuid import uuid4


class ArtifactStorage:
    """Persists generated PNG/MP4/GIF/code artifacts and constructs public URLs."""

    def __init__(self, root_dir: Path, url_prefix: str = "/media/generated") -> None:
        self.root_dir = root_dir
        self.url_prefix = url_prefix.rstrip("/")
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(
        self,
        data: bytes,
        subdir: str,
        extension: str,
        include_base64: bool = True,
    ) -> tuple[Path, str, str | None]:
        """Write binary artifact to disk and return (path, public_url, base64_str)."""
        target_dir = self.root_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.{extension.lstrip('.')}"
        file_path = target_dir / filename
        file_path.write_bytes(data)
        public_url = f"{self.url_prefix}/{subdir}/{filename}"
        encoded = base64.b64encode(data).decode("ascii") if include_base64 else None
        return file_path, public_url, encoded

    def save_file(
        self,
        source_path: Path,
        subdir: str,
        extension: str,
    ) -> tuple[Path, str]:
        """Move an existing generated file into storage without loading bytes into RAM."""
        target_dir = self.root_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.{extension.lstrip('.')}"
        dest_path = target_dir / filename
        shutil.move(str(source_path), str(dest_path))
        public_url = f"{self.url_prefix}/{subdir}/{filename}"
        return dest_path, public_url

