"""XLSX extraction utilities."""

from __future__ import annotations

from typing import Dict, Tuple


def extract_xlsx(data: bytes, ocr_enabled: bool = False) -> Tuple[str, Dict]:
    text = ""
    meta: Dict[str, object] = {}
    try:
        import io
        import openpyxl  # type: ignore
        workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        rows = []
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join([str(cell) for cell in row if cell is not None])
                if row_text:
                    rows.append(row_text)
        text = "\n".join(rows).strip()
        meta["sheet_count"] = len(workbook.worksheets)
    except Exception as exc:
        meta["error"] = str(exc)
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    return text, meta
