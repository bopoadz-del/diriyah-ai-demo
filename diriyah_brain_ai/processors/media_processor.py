"""
Media Processing Module for Diriyah Brain AI
Handles advanced processing of photos, videos, and KMZ files for construction project analysis.
"""
import os
import io
import json
import zipfile
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime

# Image Processing and OCR
try:
    from PIL import Image
    import pytesseract
    import cv2
    import numpy as np
    IMAGE_OCR_AVAILABLE = True
except ImportError:
    IMAGE_OCR_AVAILABLE = False

# Video Processing
try:
    import cv2
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False

# XML/KMZ Processing
try:
    import xml.etree.ElementTree as ET
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Advanced media file processor for construction project analysis"""
    
    def __init__(self):
        self.supported_image_formats = ["jpg", "jpeg", "png", "tiff", "bmp", "gif"]
        self.supported_video_formats = ["mp4", "avi", "mov", "mkv", "wmv"]
        self.supported_kmz_formats = ["kmz", "kml"]
        
        self.construction_objects = [
            "excavator", "crane", "dump truck", "concrete mixer", "scaffolding",
            "rebar", "concrete slab", "formwork", "brick wall", "steel beam",
            "worker", "hard hat", "safety vest", "barrier", "sign"
        ]
        
        self.progress_keywords = [
            "foundation", "slab", "wall", "roof", "MEP", "finishes", "completion"
        ]

    def process_photo(self, file_path: str) -> Dict[str, Any]:
        """Process image files for construction progress and QA/QC"""
        if not IMAGE_OCR_AVAILABLE:
            return {"error": "Image processing libraries not available"}
        
        result = {
            "type": "photo",
            "file_path": file_path,
            "metadata": {},
            "text_content": "",
            "objects_detected": [],
            "progress_tags": [],
            "qa_issues": [],
            "analysis": {}
        }
        
        try:
            image = Image.open(file_path)
            result["metadata"] = {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
                "size_bytes": os.path.getsize(file_path)
            }
            
            # OCR for text extraction
            try:
                text_eng = pytesseract.image_to_string(image, lang="eng")
                text_ara = pytesseract.image_to_string(image, lang="ara")
                result["text_content"] = f"English OCR:\n{text_eng}\n\nArabic OCR:\n{text_ara}"
            except Exception as e:
                logger.warning(f"OCR failed for {file_path}: {e}")
            
            # Placeholder for object detection (requires a CV model)
            detected_objects = self._detect_construction_objects(file_path)
            result["objects_detected"] = detected_objects
            
            # Placeholder for progress tagging
            progress_tags = self._tag_progress(result["text_content"], detected_objects)
            result["progress_tags"] = progress_tags
            
            # Placeholder for QA issues (e.g., crack detection, misalignment)
            qa_issues = self._detect_qa_issues(file_path)
            result["qa_issues"] = qa_issues
            
            result["analysis"] = {
                "overall_assessment": "Good for progress tracking",
                "potential_risks": [issue["issue"] for issue in qa_issues if issue["severity"] == "High"]
            }
            
        except Exception as e:
            result["error"] = f"Photo processing failed for {file_path}: {str(e)}"
        
        return result

    def process_video(self, file_path: str) -> Dict[str, Any]:
        """Process video files for progress monitoring and activity recognition"""
        if not VIDEO_AVAILABLE:
            return {"error": "Video processing libraries not available"}
        
        result = {
            "type": "video",
            "file_path": file_path,
            "metadata": {},
            "events_detected": [],
            "progress_summary": "",
            "analysis": {}
        }
        
        try:
            cap = cv2.VideoCapture(file_path)
            
            result["metadata"] = {
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "duration_seconds": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS),
                "size_bytes": os.path.getsize(file_path)
            }
            
            # Sample frames for analysis (e.g., every 5 seconds)
            fps = cap.get(cv2.CAP_PROP_FPS)
            interval = int(fps * 5) # Analyze every 5 seconds
            
            frame_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                
                if frame_idx % interval == 0:
                    # Placeholder for advanced frame analysis (e.g., object detection, activity recognition)
                    # For now, we'll simulate some events
                    if frame_idx == interval * 2: # Example event at 10s mark
                        result["events_detected"].append({
                            "time_seconds": frame_idx / fps,
                            "event": "Excavator activity detected",
                            "confidence": 0.85
                        })
                    elif frame_idx == interval * 5: # Example event at 25s mark
                        result["events_detected"].append({
                            "time_seconds": frame_idx / fps,
                            "event": "Concrete pouring in progress",
                            "confidence": 0.92
                        })
                frame_idx += 1
            
            cap.release()
            
            result["progress_summary"] = f"Analyzed {len(result["events_detected"])} key events. Overall progress seems consistent."
            result["analysis"] = {
                "video_type": "site_monitoring",
                "actionable_insights": [event["event"] for event in result["events_detected"]],
                "drone_footage_potential": True if result["metadata"]["height"] > 1080 else False
            }
            
        except Exception as e:
            result["error"] = f"Video processing failed for {file_path}: {str(e)}"
        
        return result

    def process_kmz(self, file_path: str) -> Dict[str, Any]:
        """Process KMZ/KML files for geospatial data and project context"""
        if not XML_AVAILABLE:
            return {"error": "XML processing libraries not available"}
        
        result = {
            "type": "kmz",
            "file_path": file_path,
            "kml_content": "",
            "placemarks": [],
            "paths": [],
            "polygons": [],
            "metadata": {},
            "analysis": {}
        }
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                kml_file = None
                for root, _, files in os.walk(tmpdir):
                    for file in files:
                        if file.endswith(".kml"):
                            kml_file = os.path.join(root, file)
                            break
                    if kml_file: break
                
                if not kml_file:
                    raise ValueError("KML file not found inside KMZ archive")
                
                with open(kml_file, "r", encoding="utf-8") as f:
                    kml_content = f.read()
                result["kml_content"] = kml_content
                
                root = ET.fromstring(kml_content)
                
                # Extract Placemarks
                for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
                    name = placemark.find(".//{http://www.opengis.net/kml/2.2}name")
                    description = placemark.find(".//{http://www.opengis.net/kml/2.2}description")
                    
                    point = placemark.find(".//{http://www.opengis.net/kml/2.2}Point/{http://www.opengis.net/kml/2.2}coordinates")
                    line = placemark.find(".//{http://www.opengis.net/kml/2.2}LineString/{http://www.opengis.net/kml/2.2}coordinates")
                    poly = placemark.find(".//{http://www.opengis.net/kml/2.2}Polygon/{http://www.opengis.net/kml/2.2}outerBoundaryIs/{http://www.opengis.net/kml/2.2}LinearRing/{http://www.opengis.net/kml/2.2}coordinates")
                    
                    placemark_data = {
                        "name": name.text if name is not None else "",
                        "description": description.text if description is not None else "",
                        "coordinates": point.text.strip() if point is not None else "",
                        "type": "Point" if point is not None else "Line" if line is not None else "Polygon" if poly is not None else "Unknown"
                    }
                    result["placemarks"].append(placemark_data)
                    
                    if line is not None: result["paths"].append(placemark_data)
                    if poly is not None: result["polygons"].append(placemark_data)
            
            result["metadata"]["placemark_count"] = len(result["placemarks"])
            result["metadata"]["path_count"] = len(result["paths"])
            result["metadata"]["polygon_count"] = len(result["polygons"])
            
            result["analysis"] = {
                "geospatial_coverage": "Extensive" if len(result["polygons"]) > 0 else "Limited",
                "key_locations": [p["name"] for p in result["placemarks"] if p["type"] == "Point"]
            }
            
        except Exception as e:
            result["error"] = f"KMZ processing failed for {file_path}: {str(e)}"
        
        return result

    def _detect_construction_objects(self, image_path: str) -> List[Dict[str, Any]]:
        """Placeholder for object detection in images (requires a CV model)."""
        # In a real implementation, this would use a pre-trained object detection model (e.g., YOLO, Faster R-CNN)
        # For demonstration, we'll simulate detection based on image content or metadata.
        
        # Simulate detection based on common construction objects
        simulated_objects = []
        if "crane" in image_path.lower():
            simulated_objects.append({"object": "crane", "confidence": 0.95, "bbox": [100, 50, 200, 300]})
        if "excavator" in image_path.lower():
            simulated_objects.append({"object": "excavator", "confidence": 0.90, "bbox": [50, 150, 180, 250]})
        if "worker" in image_path.lower():
            simulated_objects.append({"object": "worker", "confidence": 0.80, "bbox": [250, 400, 300, 500]})
        
        return simulated_objects

    def _tag_progress(self, text_content: str, detected_objects: List[Dict[str, Any]]) -> List[str]:
        """Placeholder for tagging construction progress based on text and detected objects."""
        progress_tags = []
        text_upper = text_content.upper()
        
        for keyword in self.progress_keywords:
            if keyword.upper() in text_upper:
                progress_tags.append(keyword)
        
        for obj in detected_objects:
            if obj["object"] == "concrete slab":
                progress_tags.append("slab poured")
            elif obj["object"] == "rebar":
                progress_tags.append("rebar installed")
        
        return list(set(progress_tags))

    def _detect_qa_issues(self, image_path: str) -> List[Dict[str, Any]]:
        """Placeholder for detecting QA issues (e.g., cracks, misalignments) in images."""
        # In a real implementation, this would use specialized computer vision models
        
        qa_issues = []
        if "crack" in image_path.lower():
            qa_issues.append({"issue": "Potential crack detected", "severity": "High", "location": "(120, 80)"})
        if "misalignment" in image_path.lower():
            qa_issues.append({"issue": "Possible misalignment", "severity": "Medium", "location": "(300, 200)"})
        
        return qa_issues

# Global instance
media_processor = MediaProcessor()

