from __future__ import annotations

try:  # pragma: no cover - optional CAD dependencies for Render builds
    import ezdxf  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    ezdxf = None  # type: ignore[assignment]

try:  # pragma: no cover - optional BIM dependency
    import ifcopenshell  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    ifcopenshell = None  # type: ignore[assignment]

from .drive_service import download_file

def parse_dwg(file_path: str):
    if ezdxf is None:
        raise RuntimeError("ezdxf package is not installed; DWG parsing unavailable")
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    entities = []
    for e in msp.query('LINE CIRCLE ARC LWPOLYLINE'):
        entities.append({'type': e.dxftype(), 'layer': e.dxf.layer})
    return entities

def parse_ifc(file_path: str):
    if ifcopenshell is None:
        raise RuntimeError("ifcopenshell package is not installed; IFC parsing unavailable")
    model = ifcopenshell.open(file_path)
    entities = []
    for wall in model.by_type('IfcWall'):
        entities.append({'type': 'Wall', 'name': wall.Name})
    return entities

def generate_qto(file_id: str, mime_type: str):
    local_path = download_file(file_id)
    if mime_type.endswith('dwg'):
        data = parse_dwg(local_path)
    elif mime_type.endswith('ifc'):
        data = parse_ifc(local_path)
    else:
        raise ValueError('Unsupported file format for QTO')
    return data
