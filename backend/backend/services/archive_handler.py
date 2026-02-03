"""
Archive inspection utilities for Diriyah AI.

This module contains functions to inspect common archive formats
without extracting their contents. Currently supported formats are
ZIP and TAR (including compressed variants such as ``.tar.gz`` and
``.tgz``). Unsupported formats, including RAR and 7Z, return an
informative error. Future enhancements could add extraction to
temporary directories, malware scanning and type detection.
"""

from pathlib import Path
from typing import Any, Dict, List
import zipfile
import tarfile


def list_archive_contents(file_path: Path) -> Dict[str, Any]:
    """List the entries of an archive file.

    Args:
        file_path: Path to the uploaded archive file.

    Returns:
        A dictionary containing the archive type, file count and
        entries list. If the format is unsupported or cannot be
        opened, an ``error`` message is included instead of
        ``entries``.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Archive file {file_path} does not exist")

    suffix = file_path.suffix.lower().lstrip('.')
    try:
        if suffix == 'zip':
            with zipfile.ZipFile(file_path, 'r') as zf:
                entries = zf.namelist()
                return {
                    "archive_type": "zip",
                    "file_count": len(entries),
                    "entries": entries,
                }
        elif suffix in {'tar', 'gz', 'tgz', 'bz2', 'xz'}:
            with tarfile.open(file_path, 'r:*') as tf:
                entries = [member.name for member in tf.getmembers()]
                return {
                    "archive_type": "tar",
                    "file_count": len(entries),
                    "entries": entries,
                }
        else:
            return {
                "archive_type": suffix,
                "file_count": 0,
                "error": f"Unsupported archive format: {suffix}",
            }
    except (zipfile.BadZipFile, tarfile.TarError) as exc:
        return {
            "archive_type": suffix,
            "file_count": 0,
            "error": f"Failed to read archive: {exc}",
        }