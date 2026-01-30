import os
import importlib

MODEL_PATH = os.getenv("YOLO_MODEL", "yolov8n.pt")
_model = None
_model_available = True


def _get_model():
    global _model, _model_available
    if _model is not None or not _model_available:
        return _model
    try:
        ultralytics = importlib.import_module("ultralytics")
        YOLO = getattr(ultralytics, "YOLO", None)
        if YOLO is None:
            _model_available = False
            return None
        _model = YOLO(MODEL_PATH)
    except Exception:
        _model_available = False
        return None
    return _model

def analyze_image(file_path: str):
    model = _get_model()
    if model is None:
        return []
    results = model(file_path)
    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "class": model.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": box.xyxy.tolist()
            })
    return detections
