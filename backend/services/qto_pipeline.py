import ezdxf, ifcopenshell, pandas as pd
from .drive_service import download_file

def parse_dwg(file_path: str):
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    entities = []
    for e in msp.query('LINE CIRCLE ARC LWPOLYLINE'):
        entities.append({'type': e.dxftype(), 'layer': e.dxf.layer})
    return entities

def parse_ifc(file_path: str):
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
