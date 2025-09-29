from ultralytics import YOLO
import os

MODEL_PATH = os.getenv("YOLO_MODEL", "yolov8n.pt")
model = YOLO(MODEL_PATH)

def analyze_image(file_path: str):
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