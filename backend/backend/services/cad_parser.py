"""
CAD file metadata extractor for Diriyah AI.

This module identifies whether an uploaded file has a common CAD
extension and returns basic metadata such as filename, extension and
size. For recognised CAD formats, it reports that detailed analysis
is not yet implemented but the file has been stored. For other
formats, it indicates that only basic metadata is available.

Supported CAD extensions include: ``dwg``, ``dxf``, ``dwf``,
``dgn``, ``rvt``, ``ifc``, ``step``, ``stp``, ``iges``, ``igs``,
``stl``, and ``3dm``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

SUPPORTED_CAD_EXTENSIONS = {
    ".dwg",
    ".dxf",
    ".dwf",
    ".dgn",
    ".rvt",
    ".ifc",
    ".step",
    ".stp",
    ".iges",
    ".igs",
    ".stl",
    ".3dm",
}


def parse_cad_file(file_path: Path) -> Dict[str, Any]:
    """
    Analyze a CAD or 3D model file and return simple metadata.

    Args:
        file_path: Path to the uploaded file.

    Returns:
        A dictionary containing the file name, extension, size,
        ``cad_format`` (boolean) and a descriptive message.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    file_name = file_path.name
    ext = file_path.suffix.lower()
    file_size = file_path.stat().st_size
    is_cad = ext in SUPPORTED_CAD_EXTENSIONS

    if is_cad:
        message = (
            "CAD file detected but detailed analysis is not yet implemented. "
            "The file has been stored successfully."
        )
    else:
        message = (
            "The uploaded file is not a recognised CAD format. Only basic metadata "
            "is returned."
        )

    return {
        "file_name": file_name,
        "file_ext": ext,
        "file_size": file_size,
        "cad_format": is_cad,
        "message": message,
    }