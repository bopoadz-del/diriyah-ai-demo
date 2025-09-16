"""
Aconex Extract Processing Module for Diriyah Brain AI
Handles parsing of Aconex document extracts (RFIs, Transmittals, Correspondence)
"""
import os
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class AconexProcessor:
    """Processes Aconex document extracts for key information and status"""
    
    def __init__(self):
        self.supported_document_types = ["RFI", "Transmittal", "Correspondence", "Mail"]
        self.rfi_keywords = ["RFI", "Request for Information", "Query"]
        self.transmittal_keywords = ["Transmittal", "Document Transmittal", "Submission"]
        self.correspondence_keywords = ["Correspondence", "Letter", "Memo"]
        
        self.status_keywords = {
            "Open": ["Open", "Pending", "In Progress", "Draft"],
            "Closed": ["Closed", "Answered", "Completed", "Resolved"],
            "Overdue": ["Overdue", "Late", "Expired"],
            "Approved": ["Approved", "Accepted"],
            "Rejected": ["Rejected", "Disapproved"]
        }

    def process_aconex_extract(self, text_content: str, file_name: str = "unknown_file.txt", project_context: Dict = None) -> Dict[str, Any]:
        """
        Processes a text extract from an Aconex document.
        
        Args:
            text_content: The full text content of the Aconex document.
            file_name: The name of the file being processed.
            project_context: Additional project information for context.
            
        Returns:
            Dictionary containing extracted Aconex data and analysis.
        """
        logger.info(f"Processing Aconex extract: {file_name}")
        
        analysis_result = {
            "file_name": file_name,
            "document_type": self._detect_document_type(text_content, file_name),
            "document_id": self._extract_document_id(text_content, file_name),
            "subject": self._extract_subject(text_content),
            "sender": self._extract_sender(text_content),
            "recipient": self._extract_recipient(text_content),
            "date_issued": self._extract_date(text_content, "Issued Date"),
            "due_date": self._extract_date(text_content, "Due Date"),
            "status": self._extract_status(text_content),
            "summary": self._summarize_content(text_content),
            "keywords": self._extract_keywords(text_content),
            "processing_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Aconex processing completed for {file_name}")
        return analysis_result

    def _detect_document_type(self, text: str, file_name: str) -> str:
        """Detects the type of Aconex document based on keywords and file name."""
        text_upper = text.upper()
        file_name_upper = file_name.upper()

        if any(kw in text_upper for kw in self.rfi_keywords) or "RFI" in file_name_upper:
            return "RFI"
        if any(kw in text_upper for kw in self.transmittal_keywords) or "TRANSMITTAL" in file_name_upper:
            return "Transmittal"
        if any(kw in text_upper for kw in self.correspondence_keywords) or "CORRESPONDENCE" in file_name_upper or "MAIL" in file_name_upper:
            return "Correspondence"
        
        return "Unknown Aconex Document"

    def _extract_document_id(self, text: str, file_name: str) -> Optional[str]:
        """Extracts a document ID (e.g., RFI-001, T-2023-01-005)."""
        # Common patterns for Aconex document IDs
        patterns = [
            r"RFI[-_]?\d{3,}",
            r"T[-_]?\d{4}[-_]?\d{2}[-_]?\d{3,}",
            r"CORR[-_]?\d{3,}",
            r"MAIL[-_]?\d{3,}",
            r"DOC[-_]?\d{3,}"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match: return match.group(0)
        
        # Try to extract from filename if not found in content
        file_name_match = re.search(r"([A-Z]{2,4}[-_]?\d{3,}[-_]?\d{0,})", file_name, re.IGNORECASE)
        if file_name_match: return file_name_match.group(0)

        return None

    def _extract_subject(self, text: str) -> Optional[str]:
        """Extracts the subject line."""
        match = re.search(r"Subject: (.+?)\n", text, re.IGNORECASE)
        if match: return match.group(1).strip()
        return None

    def _extract_sender(self, text: str) -> Optional[str]:
        """Extracts the sender's name."""
        match = re.search(r"From: (.+?)\n", text, re.IGNORECASE)
        if match: return match.group(1).strip()
        return None

    def _extract_recipient(self, text: str) -> Optional[str]:
        """Extracts the recipient's name."""
        match = re.search(r"To: (.+?)\n", text, re.IGNORECASE)
        if match: return match.group(1).strip()
        return None

    def _extract_date(self, text: str, label: str) -> Optional[str]:
        """Extracts a date associated with a label (e.g., 'Issued Date', 'Due Date')."""
        match = re.search(rf"{label}:\s*(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})", text, re.IGNORECASE)
        if match: return match.group(1)
        return None

    def _extract_status(self, text: str) -> str:
        """Detects the document status (Open, Closed, Overdue, Approved, Rejected)."""
        text_upper = text.upper()
        for status, keywords in self.status_keywords.items():
            if any(kw.upper() in text_upper for kw in keywords):
                return status
        return "Unknown"

    def _summarize_content(self, text: str) -> str:
        """Generates a brief summary of the document content."""
        # In a real scenario, this would use an LLM for summarization
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[:3]) + "..." if len(sentences) > 3 else text

    def _extract_keywords(self, text: str) -> List[str]:
        """Extracts relevant keywords from the document content."""
        # In a real scenario, this would use NLP techniques
        common_keywords = ["design", "construction", "site", "drawing", "schedule", "cost", "safety", "quality"]
        found_keywords = [kw for kw in common_keywords if kw in text.lower()]
        return found_keywords

# Global instance
aconex_processor = AconexProcessor()

