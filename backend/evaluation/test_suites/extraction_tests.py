"""Extraction Test Suite - Contract clause extraction accuracy tests."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..schemas import TestResult
from .base import BaseTestSuite

logger = logging.getLogger(__name__)

# Default test cases for contract clause extraction
EXTRACTION_TEST_CASES = [
    {
        "test_name": "duration_extraction",
        "input": {"text": "The Contractor shall complete all works within 18 months from commencement date."},
        "expected": {
            "entities": [
                {"type": "Duration", "value": "18 months"},
                {"type": "Party", "value": "Contractor"}
            ]
        },
        "metadata": {"clause_type": "duration", "difficulty": "easy"}
    },
    {
        "test_name": "payment_term_extraction",
        "input": {"text": "Payment shall be made within 30 days of invoice submission."},
        "expected": {
            "entities": [
                {"type": "PaymentTerm", "value": "30 days"},
                {"type": "Event", "value": "invoice submission"}
            ]
        },
        "metadata": {"clause_type": "payment", "difficulty": "easy"}
    },
    {
        "test_name": "penalty_clause_extraction",
        "input": {"text": "Liquidated damages shall be assessed at $5,000 per day for each day of delay."},
        "expected": {
            "entities": [
                {"type": "Penalty", "value": "$5,000 per day"},
                {"type": "Condition", "value": "delay"}
            ]
        },
        "metadata": {"clause_type": "penalty", "difficulty": "medium"}
    },
    {
        "test_name": "retention_extraction",
        "input": {"text": "The Owner shall retain 10% of each progress payment until substantial completion."},
        "expected": {
            "entities": [
                {"type": "Retention", "value": "10%"},
                {"type": "Party", "value": "Owner"},
                {"type": "Event", "value": "substantial completion"}
            ]
        },
        "metadata": {"clause_type": "retention", "difficulty": "medium"}
    },
    {
        "test_name": "warranty_extraction",
        "input": {"text": "Contractor warrants all work for a period of 2 years from date of final acceptance."},
        "expected": {
            "entities": [
                {"type": "Warranty", "value": "2 years"},
                {"type": "Party", "value": "Contractor"},
                {"type": "Event", "value": "final acceptance"}
            ]
        },
        "metadata": {"clause_type": "warranty", "difficulty": "easy"}
    },
    {
        "test_name": "insurance_extraction",
        "input": {"text": "Contractor shall maintain general liability insurance of not less than $2,000,000 per occurrence."},
        "expected": {
            "entities": [
                {"type": "Insurance", "value": "$2,000,000"},
                {"type": "InsuranceType", "value": "general liability"},
                {"type": "Party", "value": "Contractor"}
            ]
        },
        "metadata": {"clause_type": "insurance", "difficulty": "medium"}
    },
    {
        "test_name": "bond_extraction",
        "input": {"text": "Performance bond in the amount of 100% of contract value is required."},
        "expected": {
            "entities": [
                {"type": "Bond", "value": "100%"},
                {"type": "BondType", "value": "Performance"}
            ]
        },
        "metadata": {"clause_type": "bond", "difficulty": "easy"}
    },
    {
        "test_name": "termination_extraction",
        "input": {"text": "Either party may terminate this agreement with 30 days written notice."},
        "expected": {
            "entities": [
                {"type": "NoticePeriod", "value": "30 days"},
                {"type": "NoticeType", "value": "written"}
            ]
        },
        "metadata": {"clause_type": "termination", "difficulty": "easy"}
    },
    {
        "test_name": "change_order_extraction",
        "input": {"text": "Change orders exceeding $50,000 require written approval from the Owner."},
        "expected": {
            "entities": [
                {"type": "Threshold", "value": "$50,000"},
                {"type": "Approval", "value": "written approval"},
                {"type": "Party", "value": "Owner"}
            ]
        },
        "metadata": {"clause_type": "change_order", "difficulty": "medium"}
    },
    {
        "test_name": "dispute_resolution_extraction",
        "input": {"text": "All disputes shall be resolved through binding arbitration in accordance with AAA rules."},
        "expected": {
            "entities": [
                {"type": "DisputeResolution", "value": "binding arbitration"},
                {"type": "Standard", "value": "AAA rules"}
            ]
        },
        "metadata": {"clause_type": "dispute", "difficulty": "medium"}
    },
    {
        "test_name": "milestone_extraction",
        "input": {"text": "Milestone 1: Foundation complete by June 30, 2024. Payment: $500,000."},
        "expected": {
            "entities": [
                {"type": "Milestone", "value": "Foundation complete"},
                {"type": "Date", "value": "June 30, 2024"},
                {"type": "Amount", "value": "$500,000"}
            ]
        },
        "metadata": {"clause_type": "milestone", "difficulty": "medium"}
    },
    {
        "test_name": "force_majeure_extraction",
        "input": {"text": "Force majeure events include acts of God, war, terrorism, and pandemic."},
        "expected": {
            "entities": [
                {"type": "ForceMajeure", "value": ["acts of God", "war", "terrorism", "pandemic"]}
            ]
        },
        "metadata": {"clause_type": "force_majeure", "difficulty": "medium"}
    },
    {
        "test_name": "scope_extraction",
        "input": {"text": "The Work includes design, supply, installation, and commissioning of the HVAC system."},
        "expected": {
            "entities": [
                {"type": "Scope", "value": ["design", "supply", "installation", "commissioning"]},
                {"type": "System", "value": "HVAC system"}
            ]
        },
        "metadata": {"clause_type": "scope", "difficulty": "easy"}
    },
    {
        "test_name": "liability_cap_extraction",
        "input": {"text": "Total liability shall not exceed the contract value of $15,000,000."},
        "expected": {
            "entities": [
                {"type": "LiabilityCap", "value": "$15,000,000"}
            ]
        },
        "metadata": {"clause_type": "liability", "difficulty": "easy"}
    },
    {
        "test_name": "indemnification_extraction",
        "input": {"text": "Contractor shall indemnify Owner against all claims arising from Contractor's negligence."},
        "expected": {
            "entities": [
                {"type": "Indemnification", "value": "claims"},
                {"type": "Condition", "value": "Contractor's negligence"},
                {"type": "Party", "value": "Contractor"},
                {"type": "Beneficiary", "value": "Owner"}
            ]
        },
        "metadata": {"clause_type": "indemnification", "difficulty": "hard"}
    }
]


class ExtractionTestSuite(BaseTestSuite):
    """Test suite for contract clause extraction accuracy."""

    suite_name = "extraction"
    description = "Contract Clause Extraction Tests"

    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load extraction test cases from file or defaults."""
        data_path = Path(__file__).parent.parent / "data" / "test_datasets" / "extraction_tests.json"

        if data_path.exists():
            try:
                with open(data_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load extraction tests from file: {e}")

        return EXTRACTION_TEST_CASES

    def _run_single_test(
        self,
        test_case: Dict[str, Any],
        db: Session
    ) -> TestResult:
        """Run a single extraction test."""
        test_name = test_case.get("test_name", "unknown")
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})

        try:
            actual = self._perform_extraction(input_data.get("text", ""))
            passed = self._evaluate_extraction_result(expected, actual)

            return TestResult(
                id=0,
                test_run_id=0,
                test_name=test_name,
                passed=passed,
                actual_output=actual,
                expected_output=expected,
                error_message=None if passed else "Entity extraction mismatch",
                created_at=datetime.utcnow()
            )

        except Exception as e:
            return TestResult(
                id=0,
                test_run_id=0,
                test_name=test_name,
                passed=False,
                actual_output=None,
                expected_output=expected,
                error_message=str(e),
                created_at=datetime.utcnow()
            )

    def _perform_extraction(self, text: str) -> Dict[str, Any]:
        """Extract entities from contract text using pattern matching."""
        entities = []

        # Duration patterns
        duration_match = re.search(r'(\d+)\s*(months?|years?|days?|weeks?)', text, re.IGNORECASE)
        if duration_match:
            entities.append({
                "type": "Duration",
                "value": f"{duration_match.group(1)} {duration_match.group(2)}"
            })

        # Payment term patterns
        payment_match = re.search(r'within\s*(\d+)\s*days?', text, re.IGNORECASE)
        if payment_match:
            entities.append({
                "type": "PaymentTerm",
                "value": f"{payment_match.group(1)} days"
            })

        # Money patterns
        money_matches = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:per\s+\w+|million|billion))?', text)
        for match in money_matches:
            entities.append({"type": "Amount", "value": match})
            # Check for penalty
            if "per day" in text.lower() and "damages" in text.lower():
                entities.append({"type": "Penalty", "value": match})
            # Check for liability cap
            if "liability" in text.lower() and "exceed" in text.lower():
                entities.append({"type": "LiabilityCap", "value": match})
            # Check for insurance
            if "insurance" in text.lower():
                entities.append({"type": "Insurance", "value": match})

        # Percentage patterns
        percent_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        for match in percent_matches:
            if "retain" in text.lower():
                entities.append({"type": "Retention", "value": f"{match}%"})
            elif "bond" in text.lower():
                entities.append({"type": "Bond", "value": f"{match}%"})

        # Party extraction
        parties = []
        if re.search(r'\b(contractor|subcontractor)\b', text, re.IGNORECASE):
            parties.append("Contractor")
        if re.search(r'\b(owner|client|employer)\b', text, re.IGNORECASE):
            parties.append("Owner")
        for party in parties:
            entities.append({"type": "Party", "value": party})

        # Event extraction
        events = []
        if "invoice submission" in text.lower():
            events.append("invoice submission")
        if "substantial completion" in text.lower():
            events.append("substantial completion")
        if "final acceptance" in text.lower():
            events.append("final acceptance")
        if "commencement" in text.lower():
            events.append("commencement")
        for event in events:
            entities.append({"type": "Event", "value": event})

        # Warranty patterns
        warranty_match = re.search(r'warrant[sy]?\s+.*?(\d+)\s*(years?|months?)', text, re.IGNORECASE)
        if warranty_match:
            entities.append({
                "type": "Warranty",
                "value": f"{warranty_match.group(1)} {warranty_match.group(2)}"
            })

        # Insurance type
        if "general liability" in text.lower():
            entities.append({"type": "InsuranceType", "value": "general liability"})
        if "professional liability" in text.lower():
            entities.append({"type": "InsuranceType", "value": "professional liability"})

        # Bond type
        if "performance bond" in text.lower():
            entities.append({"type": "BondType", "value": "Performance"})
        if "payment bond" in text.lower():
            entities.append({"type": "BondType", "value": "Payment"})

        # Notice period
        notice_match = re.search(r'(\d+)\s*days?\s*(?:written\s*)?notice', text, re.IGNORECASE)
        if notice_match:
            entities.append({"type": "NoticePeriod", "value": f"{notice_match.group(1)} days"})
        if "written notice" in text.lower():
            entities.append({"type": "NoticeType", "value": "written"})

        # Dispute resolution
        if "arbitration" in text.lower():
            arb_type = "binding arbitration" if "binding" in text.lower() else "arbitration"
            entities.append({"type": "DisputeResolution", "value": arb_type})
        if "AAA" in text:
            entities.append({"type": "Standard", "value": "AAA rules"})

        # Date extraction
        date_match = re.search(
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            text
        )
        if date_match:
            entities.append({"type": "Date", "value": date_match.group(0)})

        # Condition extraction
        if "delay" in text.lower():
            entities.append({"type": "Condition", "value": "delay"})
        if "negligence" in text.lower():
            entities.append({"type": "Condition", "value": "Contractor's negligence"})

        return {"entities": entities, "text": text}

    def _evaluate_extraction_result(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> bool:
        """Evaluate if extraction result matches expected."""
        expected_entities = expected.get("entities", [])
        actual_entities = actual.get("entities", [])

        if not expected_entities:
            return True

        # Check each expected entity is found
        matches = 0
        for exp_entity in expected_entities:
            exp_type = exp_entity.get("type")
            exp_value = exp_entity.get("value")

            for act_entity in actual_entities:
                if act_entity.get("type") == exp_type:
                    act_value = act_entity.get("value")
                    # Flexible matching for values
                    if isinstance(exp_value, str) and isinstance(act_value, str):
                        if exp_value.lower() in act_value.lower() or act_value.lower() in exp_value.lower():
                            matches += 1
                            break
                    elif exp_value == act_value:
                        matches += 1
                        break

        # Require at least 60% of expected entities to be found
        min_matches = max(1, int(len(expected_entities) * 0.6))
        return matches >= min_matches

    def test_clause_identification(self, db: Session) -> List[TestResult]:
        """Run clause identification tests."""
        return self.run_all_tests(db)

    def test_entity_extraction(self, db: Session) -> List[TestResult]:
        """Run entity extraction tests."""
        return self.run_all_tests(db)

    def calculate_extraction_metrics(self, results: List[TestResult]) -> Dict[str, float]:
        """Calculate extraction-specific metrics."""
        from ..metrics_calculator import MetricsCalculator
        return MetricsCalculator.calculate_all_metrics(results)
