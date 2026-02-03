"""
Schedule file parser for Diriyah AI.

This module provides a simple parser for Primavera P6 XER files and
Microsoft Project XML/MPP files. It detects the file type based on
extension, extracts a list of tasks and their dependencies, and then
computes schedule metrics using the critical path algorithm defined
in :mod:`schedule_metrics`. Unsupported formats return basic
metadata with an informative message.
"""

from pathlib import Path
from typing import Any, Dict, List

from .schedule_metrics import compute_critical_path


def parse_schedule_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse a schedule file and return extracted tasks and analysis.

    Args:
        file_path: Path to the uploaded schedule file.

    Returns:
        A dictionary containing filename, file size, detected format,
        parsed tasks, task count, and an ``analysis`` field. If the
        format is unsupported, ``analysis`` describes the issue.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")

    suffix = file_path.suffix.lower().lstrip('.')
    result: Dict[str, Any] = {
        "filename": file_path.name,
        "file_size": file_path.stat().st_size,
    }

    if suffix == 'xer':
        tasks = _parse_xer(file_path)
        metrics = compute_critical_path(tasks) if tasks else None
        result.update({
            "format": "XER",
            "tasks": tasks,
            "task_count": len(tasks),
            "analysis": metrics,
        })
    elif suffix in {'xml', 'mpp'}:
        tasks = _parse_mpp_xml(file_path)
        metrics = compute_critical_path(tasks) if tasks else None
        result.update({
            "format": "XML",
            "tasks": tasks,
            "task_count": len(tasks),
            "analysis": metrics,
        })
    else:
        # Unsupported formats: return basic metadata and message
        try:
            content = file_path.read_text(errors="ignore")
            line_count = len(content.splitlines())
        except Exception:
            line_count = 0
        result.update({
            "format": suffix or "unknown",
            "analysis": {
                "summary": "Unsupported schedule format",
                "line_count": line_count,
                "details": "Only XER and MPP/XML formats are supported at this time.",
            },
        })
    return result


def _parse_xer(file_path: Path) -> List[Dict[str, Any]]:
    """Extract tasks from a Primavera P6 XER file.

    This simplified parser treats any line with at least five tab‑separated
    columns as a task record and maps the first five columns to ID,
    WBS code, name, start and finish dates. Real XER files contain
    multiple tables and require more sophisticated parsing.

    Args:
        file_path: Path to the XER file.

    Returns:
        A list of task dictionaries.
    """
    tasks: List[Dict[str, Any]] = []
    try:
        with file_path.open('r', errors='ignore') as f:
            for line in f:
                if not line.strip() or line.startswith('%'):
                    continue
                cols = line.rstrip('\n').split('\t')
                if len(cols) >= 5:
                    tasks.append({
                        "id": cols[0].strip(),
                        "wbs": cols[1].strip(),
                        "name": cols[2].strip(),
                        "start": cols[3].strip(),
                        "finish": cols[4].strip(),
                    })
    except Exception:
        pass
    return tasks


def _parse_mpp_xml(file_path: Path) -> List[Dict[str, Any]]:
    """Extract tasks from an MS Project XML (or exported MPP) file.

    Finds ``Task`` elements and reads UID, Name, Start, Finish and
    PredecessorUID values. Returns a list of task dictionaries with
    optional ``dependencies`` lists.

    Args:
        file_path: Path to the XML/MPP file.

    Returns:
        A list of task dictionaries.
    """
    tasks: List[Dict[str, Any]] = []
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(file_path)
        root = tree.getroot()
        for task_elem in root.iterfind('.//Task'):
            try:
                uid_elem = task_elem.find('UID')
                name_elem = task_elem.find('Name')
                start_elem = task_elem.find('Start')
                finish_elem = task_elem.find('Finish')
                uid = uid_elem.text.strip() if uid_elem is not None and uid_elem.text else ''
                name = name_elem.text.strip() if name_elem is not None and name_elem.text else ''
                start = start_elem.text.strip() if start_elem is not None and start_elem.text else ''
                finish = finish_elem.text.strip() if finish_elem is not None and finish_elem.text else ''
                dependencies: List[str] = []
                for pred_link in task_elem.findall('PredecessorLink'):
                    pred_uid_elem = pred_link.find('PredecessorUID')
                    if pred_uid_elem is not None and pred_uid_elem.text:
                        dependencies.append(pred_uid_elem.text.strip())
                tasks.append({
                    "id": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "dependencies": dependencies,
                })
            except Exception:
                continue
    except Exception:
        pass
    return tasks