"""Commercial Pack for linking Cost items, Payment Certificates, Variations, and Invoices."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from backend.reasoning.schemas import (
    Entity,
    EntityType,
    Evidence,
    EvidenceType,
    LinkType,
    PackConfig,
)
from backend.reasoning.packs.base_pack import BasePack

logger = logging.getLogger(__name__)


# Cost code patterns commonly used in construction
COST_CODE_PATTERNS = {
    "wbs": r'\b(\d{1,2}\.\d{2}\.\d{2}(?:\.\d{2})?)\b',  # WBS format: 01.02.03.04
    "cost_center": r'\b(CC[-/]?\d{4,8})\b',  # Cost Center: CC-12345
    "activity": r'\b(ACT[-/]?\d{4,8})\b',  # Activity: ACT-12345
    "budget_line": r'\b(BL[-/]?\d{3,6})\b',  # Budget Line: BL-001
}

# Payment/commercial keywords
COMMERCIAL_KEYWORDS: Dict[str, Set[str]] = {
    "payment": {"payment", "pay", "paid", "payable", "receivable", "remittance", "transfer"},
    "invoice": {"invoice", "inv", "bill", "billing", "debit", "credit"},
    "variation": {"variation", "vo", "change", "amendment", "modification", "addendum"},
    "certificate": {"certificate", "cert", "ipc", "pc", "valuation", "interim"},
    "cost": {"cost", "expense", "expenditure", "budget", "estimate", "actual"},
    "contract": {"contract", "agreement", "scope", "terms", "conditions"},
    "retention": {"retention", "retainage", "holdback", "withheld"},
    "advance": {"advance", "mobilization", "prepayment", "deposit"},
}


class CommercialPack(BasePack):
    """
    Commercial Pack for linking Cost items, Payment Certificates, Variations, and Invoices.

    This pack specializes in:
    - Cost Item ↔ Payment Certificate linking via cost codes and amounts
    - Payment ↔ Variation Order linking via VO references
    - Variation ↔ Invoice linking via reference numbers
    - Cross-referencing commercial documents by dates, amounts, and parties
    """

    @classmethod
    def get_default_config(cls) -> PackConfig:
        """Return default configuration for CommercialPack."""
        return PackConfig(
            name="CommercialPack",
            version="1.0.0",
            description="Links cost items to payments, variations, and invoices",
            entity_types=[
                EntityType.COST_ITEM,
                EntityType.PAYMENT_CERT,
                EntityType.VARIATION_ORDER,
                EntityType.INVOICE,
            ],
            link_types=[
                LinkType.PAYS_FOR,
                LinkType.PAID_BY,
                LinkType.VARIES,
                LinkType.VARIED_BY,
                LinkType.INVOICES,
                LinkType.INVOICED_BY,
                LinkType.REFERENCES,
                LinkType.REFERENCED_BY,
            ],
            confidence_threshold=0.75,
            semantic_weight=0.5,
            keyword_weight=0.5,
            settings={
                "cost_code_weight": 0.30,
                "amount_match_weight": 0.25,
                "date_proximity_weight": 0.15,
                "reference_match_weight": 0.20,
                "amount_tolerance_percent": 5.0,  # Allow 5% variance in amount matching
                "date_proximity_days": 30,  # Consider dates within 30 days as proximate
            },
        )

    def extract_entities(
        self,
        content: str,
        document_id: str,
        document_name: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Entity]:
        """
        Extract commercial entities from document content.

        Handles cost items, payment certificates, variation orders, and invoices.
        """
        metadata = metadata or {}
        entities: List[Entity] = []

        doc_type_lower = document_type.lower()

        if doc_type_lower in ("cost", "budget", "estimate", "cost breakdown"):
            entities.extend(self._extract_cost_items(content, document_id, document_name, metadata))
        elif doc_type_lower in ("payment", "certificate", "ipc", "payment certificate"):
            entities.extend(self._extract_payment_certs(content, document_id, document_name, metadata))
        elif doc_type_lower in ("variation", "vo", "change order", "variation order"):
            entities.extend(self._extract_variations(content, document_id, document_name, metadata))
        elif doc_type_lower in ("invoice", "bill", "inv"):
            entities.extend(self._extract_invoices(content, document_id, document_name, metadata))
        else:
            # Try to extract all types from generic document
            entities.extend(self._extract_cost_items(content, document_id, document_name, metadata))
            entities.extend(self._extract_payment_certs(content, document_id, document_name, metadata))
            entities.extend(self._extract_variations(content, document_id, document_name, metadata))
            entities.extend(self._extract_invoices(content, document_id, document_name, metadata))

        logger.info(
            "Extracted %d commercial entities from %s (%s)",
            len(entities),
            document_name,
            document_type,
        )

        return entities

    def match_entities(
        self,
        source_entities: List[Entity],
        target_entities: List[Entity],
        embeddings: Optional[Dict[str, np.ndarray]] = None,
    ) -> List[Tuple[Entity, Entity, LinkType, float, List[Evidence]]]:
        """
        Find matching entity pairs with commercial-specific logic.

        Matches are based on:
        - Cost code alignment
        - Amount matching (within tolerance)
        - Date proximity
        - Reference number matches
        - Semantic similarity
        """
        embeddings = embeddings or {}
        matches: List[Tuple[Entity, Entity, LinkType, float, List[Evidence]]] = []

        for source in source_entities:
            for target in target_entities:
                if not self.should_link(source, target):
                    continue

                # Determine link type
                link_type = self._determine_link_type(source.type, target.type)
                if link_type is None:
                    continue

                # Collect evidence
                evidence = self._collect_evidence(source, target, embeddings)

                if not evidence:
                    continue

                # Calculate confidence
                confidence = self.calculate_confidence(source, target, evidence)

                if confidence >= self._config.confidence_threshold:
                    matches.append((source, target, link_type, confidence, evidence))

        logger.debug(
            "Found %d commercial matches from %d source x %d target entities",
            len(matches),
            len(source_entities),
            len(target_entities),
        )

        return matches

    def calculate_confidence(
        self,
        source: Entity,
        target: Entity,
        evidence: List[Evidence],
    ) -> float:
        """
        Calculate overall confidence from evidence items.

        Commercial matches prioritize exact reference and amount matches.
        """
        if not evidence:
            return 0.0

        total_weight = sum(e.weight for e in evidence)
        if total_weight == 0:
            return 0.0

        # Weighted average
        weighted_sum = sum(
            float(e.value) * e.weight if isinstance(e.value, (int, float)) else e.weight * 0.8
            for e in evidence
        )

        base_confidence = weighted_sum / total_weight

        # Boost for exact reference matches
        ref_evidence = [e for e in evidence if e.type == EvidenceType.CLAUSE_REFERENCE]
        if ref_evidence:
            base_confidence = min(1.0, base_confidence + 0.15)

        # Boost for matching amounts
        amount_evidence = [e for e in evidence if e.type == EvidenceType.QUANTITY_REFERENCE]
        if amount_evidence and any(float(e.value) >= 0.95 for e in amount_evidence if isinstance(e.value, (int, float))):
            base_confidence = min(1.0, base_confidence + 0.1)

        return round(base_confidence, 3)

    def should_link(self, source: Entity, target: Entity) -> bool:
        """Check if entities should be considered for linking."""
        if not super().should_link(source, target):
            return False

        # Define valid entity type combinations for commercial linking
        valid_combinations = {
            # Cost to Payment
            (EntityType.COST_ITEM, EntityType.PAYMENT_CERT),
            (EntityType.PAYMENT_CERT, EntityType.COST_ITEM),
            # Cost to Variation
            (EntityType.COST_ITEM, EntityType.VARIATION_ORDER),
            (EntityType.VARIATION_ORDER, EntityType.COST_ITEM),
            # Cost to Invoice
            (EntityType.COST_ITEM, EntityType.INVOICE),
            (EntityType.INVOICE, EntityType.COST_ITEM),
            # Payment to Variation
            (EntityType.PAYMENT_CERT, EntityType.VARIATION_ORDER),
            (EntityType.VARIATION_ORDER, EntityType.PAYMENT_CERT),
            # Payment to Invoice
            (EntityType.PAYMENT_CERT, EntityType.INVOICE),
            (EntityType.INVOICE, EntityType.PAYMENT_CERT),
            # Variation to Invoice
            (EntityType.VARIATION_ORDER, EntityType.INVOICE),
            (EntityType.INVOICE, EntityType.VARIATION_ORDER),
        }

        return (source.type, target.type) in valid_combinations

    # -------------------------------------------------------------------------
    # Entity extraction methods
    # -------------------------------------------------------------------------

    def _extract_cost_items(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract cost items from content."""
        entities: List[Entity] = []

        # Pattern for cost line items
        cost_patterns = [
            # WBS-style: 01.02.03 Description 1,234,567.89
            r'(\d{1,2}\.\d{2}\.\d{2}(?:\.\d{2})?)\s+([^0-9\n]+?)\s+([0-9,]+(?:\.\d{2})?)',
            # Budget line: BL-001 Description Amount
            r'(BL[-/]?\d{3,6})\s+([^0-9\n]+?)\s+([0-9,]+(?:\.\d{2})?)',
            # Generic: Item/Cost Code Description Amount
            r'(?:Item|Cost\s*Code)\s*[:.]?\s*([A-Z0-9][-/A-Z0-9]{2,10})\s+([^0-9\n]+?)\s+([0-9,]+(?:\.\d{2})?)',
        ]

        for pattern in cost_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                cost_code = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')

                entity_id = f"{document_id}-COST-{cost_code}"
                if self.get_cached_entity(entity_id):
                    continue

                try:
                    amount = float(amount_str)
                except ValueError:
                    amount = None

                entity = Entity(
                    id=entity_id,
                    type=EntityType.COST_ITEM,
                    text=description,
                    document_id=document_id,
                    document_name=document_name,
                    section=cost_code,
                    metadata={
                        "cost_code": cost_code,
                        "amount": amount,
                        "currency": metadata.get("currency", "USD"),
                        "references": self._extract_commercial_references(description),
                        **metadata,
                    },
                )
                entities.append(entity)
                self.cache_entity(entity)

        return entities

    def _extract_payment_certs(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract payment certificates from content."""
        entities: List[Entity] = []

        # Pattern for payment certificates
        cert_patterns = [
            # IPC No. 5, Payment Certificate #3
            r'(?:IPC|Payment\s*Cert(?:ificate)?|PC)\s*(?:No\.?|#)\s*(\d+)',
            # Certificate of Payment 2024-05
            r'(?:Certificate\s+of\s+Payment)\s*(\d{4}[-/]\d{2})',
        ]

        for pattern in cert_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                cert_number = match.group(1)

                entity_id = f"{document_id}-PC-{cert_number}"
                if self.get_cached_entity(entity_id):
                    continue

                # Extract surrounding context
                start = max(0, match.start() - 200)
                end = min(len(content), match.end() + 500)
                context = content[start:end]

                # Try to extract amounts from context
                amounts = self._extract_amounts(context)
                cert_amount = amounts[0] if amounts else None

                # Try to extract date
                cert_date = self._extract_date(context)

                # Extract related references
                vo_refs = re.findall(r'(?:VO|Variation)\s*(?:No\.?|#)\s*(\d+)', context, re.IGNORECASE)
                inv_refs = re.findall(r'(?:Invoice|INV)\s*(?:No\.?|#)\s*([A-Z0-9-]+)', context, re.IGNORECASE)

                entity = Entity(
                    id=entity_id,
                    type=EntityType.PAYMENT_CERT,
                    text=context.strip(),
                    document_id=document_id,
                    document_name=document_name,
                    section=cert_number,
                    metadata={
                        "certificate_number": cert_number,
                        "amount": cert_amount,
                        "date": cert_date,
                        "variation_refs": vo_refs,
                        "invoice_refs": inv_refs,
                        "currency": metadata.get("currency", "USD"),
                        **metadata,
                    },
                )
                entities.append(entity)
                self.cache_entity(entity)

        return entities

    def _extract_variations(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract variation orders from content."""
        entities: List[Entity] = []

        # Pattern for variation orders
        vo_patterns = [
            # VO No. 5, Variation Order #3, Change Order CO-001
            r'(?:VO|Variation\s*Order|Change\s*Order|CO)\s*(?:No\.?|#)?\s*([A-Z0-9][-A-Z0-9]*\d+)',
            # Variation 2024-001
            r'Variation\s+(\d{4}[-/]\d{3})',
        ]

        for pattern in vo_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                vo_number = match.group(1)

                entity_id = f"{document_id}-VO-{vo_number}"
                if self.get_cached_entity(entity_id):
                    continue

                # Extract surrounding context
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 600)
                context = content[start:end]

                # Extract amounts (may have original, revised, variation amount)
                amounts = self._extract_amounts(context)

                # Try to extract date
                vo_date = self._extract_date(context)

                # Extract cost code references
                cost_codes = self._extract_cost_codes(context)

                entity = Entity(
                    id=entity_id,
                    type=EntityType.VARIATION_ORDER,
                    text=context.strip(),
                    document_id=document_id,
                    document_name=document_name,
                    section=vo_number,
                    metadata={
                        "vo_number": vo_number,
                        "amounts": amounts,
                        "variation_amount": amounts[-1] if amounts else None,
                        "date": vo_date,
                        "cost_codes": cost_codes,
                        "status": self._extract_status(context),
                        "currency": metadata.get("currency", "USD"),
                        **metadata,
                    },
                )
                entities.append(entity)
                self.cache_entity(entity)

        return entities

    def _extract_invoices(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract invoices from content."""
        entities: List[Entity] = []

        # Pattern for invoices
        invoice_patterns = [
            # Invoice No. INV-2024-001, Invoice #12345
            r'(?:Invoice|INV)\s*(?:No\.?|#)\s*([A-Z0-9][-A-Z0-9]+)',
            # Bill No. BILL-001
            r'(?:Bill)\s*(?:No\.?|#)\s*([A-Z0-9][-A-Z0-9]+)',
        ]

        for pattern in invoice_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                inv_number = match.group(1)

                entity_id = f"{document_id}-INV-{inv_number}"
                if self.get_cached_entity(entity_id):
                    continue

                # Extract surrounding context
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 500)
                context = content[start:end]

                # Extract amounts
                amounts = self._extract_amounts(context)
                total_amount = amounts[-1] if amounts else None

                # Extract date
                inv_date = self._extract_date(context)

                # Extract related references
                vo_refs = re.findall(r'(?:VO|Variation)\s*(?:No\.?|#)\s*(\d+)', context, re.IGNORECASE)
                po_refs = re.findall(r'(?:PO|Purchase\s*Order)\s*(?:No\.?|#)\s*([A-Z0-9-]+)', context, re.IGNORECASE)

                entity = Entity(
                    id=entity_id,
                    type=EntityType.INVOICE,
                    text=context.strip(),
                    document_id=document_id,
                    document_name=document_name,
                    section=inv_number,
                    metadata={
                        "invoice_number": inv_number,
                        "amount": total_amount,
                        "amounts": amounts,
                        "date": inv_date,
                        "variation_refs": vo_refs,
                        "po_refs": po_refs,
                        "currency": metadata.get("currency", "USD"),
                        **metadata,
                    },
                )
                entities.append(entity)
                self.cache_entity(entity)

        return entities

    # -------------------------------------------------------------------------
    # Evidence collection methods
    # -------------------------------------------------------------------------

    def _collect_evidence(
        self,
        source: Entity,
        target: Entity,
        embeddings: Dict[str, np.ndarray],
    ) -> List[Evidence]:
        """Collect all evidence for a potential commercial link."""
        evidence: List[Evidence] = []
        settings = self._config.settings

        # 1. Cost code matching
        cost_code_evidence = self._check_cost_code_match(source, target)
        if cost_code_evidence:
            cost_code_evidence.weight = settings.get("cost_code_weight", 0.30)
            evidence.append(cost_code_evidence)

        # 2. Amount matching
        amount_evidence = self._check_amount_match(source, target)
        if amount_evidence:
            amount_evidence.weight = settings.get("amount_match_weight", 0.25)
            evidence.append(amount_evidence)

        # 3. Reference matching (VO refs, invoice refs, etc.)
        ref_evidence = self._check_reference_match(source, target)
        if ref_evidence:
            ref_evidence.weight = settings.get("reference_match_weight", 0.20)
            evidence.append(ref_evidence)

        # 4. Date proximity
        date_evidence = self._check_date_proximity(source, target)
        if date_evidence:
            date_evidence.weight = settings.get("date_proximity_weight", 0.15)
            evidence.append(date_evidence)

        # 5. Keyword matching
        keyword_score, matched_keywords = self.compute_keyword_match(
            source, target, self._get_domain_keywords()
        )
        if keyword_score >= 0.1 and matched_keywords:
            evidence.append(
                self.build_evidence(
                    EvidenceType.KEYWORD_MATCH,
                    keyword_score,
                    self._config.keyword_weight * 0.5,  # Lower weight for keywords in commercial
                    metadata={"matched_keywords": matched_keywords},
                )
            )

        # 6. Semantic similarity
        source_emb = embeddings.get(source.id)
        target_emb = embeddings.get(target.id)
        if source_emb is not None and target_emb is not None:
            similarity = self.compute_semantic_similarity(source_emb, target_emb)
            if similarity >= 0.4:
                evidence.append(
                    self.build_evidence(
                        EvidenceType.SEMANTIC_SIMILARITY,
                        similarity,
                        self._config.semantic_weight,
                    )
                )

        return evidence

    def _check_cost_code_match(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check for cost code matches between entities."""
        source_codes = set(source.metadata.get("cost_codes", []))
        if source.section:
            source_codes.add(source.section)

        target_codes = set(target.metadata.get("cost_codes", []))
        if target.section and target.type == EntityType.COST_ITEM:
            target_codes.add(target.section)

        # Also extract from text if needed
        if not source_codes:
            source_codes = set(self._extract_cost_codes(source.text))
        if not target_codes:
            target_codes = set(self._extract_cost_codes(target.text))

        if not source_codes or not target_codes:
            return None

        matched = source_codes & target_codes
        if not matched:
            # Check for partial matches (same WBS prefix)
            for sc in source_codes:
                for tc in target_codes:
                    if sc[:5] == tc[:5] and len(sc) >= 5:  # Same 2-level WBS
                        matched.add(f"{sc[:5]}*")

        if not matched:
            return None

        exact_matches = [c for c in matched if not c.endswith('*')]
        score = 1.0 if exact_matches else 0.7

        return self.build_evidence(
            EvidenceType.COST_CODE_MATCH,
            score,
            0.30,
            source_text=", ".join(source_codes),
            target_text=", ".join(target_codes),
            metadata={"matched_codes": list(matched)},
        )

    def _check_amount_match(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check if amounts match within tolerance."""
        source_amount = source.metadata.get("amount")
        target_amount = target.metadata.get("amount")

        # Also check variation_amount for VOs
        if source_amount is None:
            source_amount = source.metadata.get("variation_amount")
        if target_amount is None:
            target_amount = target.metadata.get("variation_amount")

        if source_amount is None or target_amount is None:
            return None

        try:
            source_val = float(source_amount)
            target_val = float(target_amount)
        except (TypeError, ValueError):
            return None

        if source_val == 0 or target_val == 0:
            return None

        # Calculate percentage difference
        diff_percent = abs(source_val - target_val) / max(source_val, target_val) * 100
        tolerance = self._config.settings.get("amount_tolerance_percent", 5.0)

        if diff_percent > tolerance:
            return None

        # Score inversely proportional to difference
        score = 1.0 - (diff_percent / tolerance) * 0.3

        return self.build_evidence(
            EvidenceType.QUANTITY_REFERENCE,
            score,
            0.25,
            source_text=f"{source_val:,.2f}",
            target_text=f"{target_val:,.2f}",
            metadata={
                "source_amount": source_val,
                "target_amount": target_val,
                "difference_percent": round(diff_percent, 2),
            },
        )

    def _check_reference_match(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check for matching references (VO numbers, invoice numbers, etc.)."""
        matched_refs: List[str] = []

        # Check variation references
        source_vo_refs = set(source.metadata.get("variation_refs", []))
        target_vo_refs = set(target.metadata.get("variation_refs", []))

        # If target is a VO, check if source references it
        if target.type == EntityType.VARIATION_ORDER and target.section:
            if target.section in source_vo_refs or target.metadata.get("vo_number") in source_vo_refs:
                matched_refs.append(f"VO-{target.section}")

        # If source is a VO, check if target references it
        if source.type == EntityType.VARIATION_ORDER and source.section:
            if source.section in target_vo_refs or source.metadata.get("vo_number") in target_vo_refs:
                matched_refs.append(f"VO-{source.section}")

        # Check invoice references
        source_inv_refs = set(source.metadata.get("invoice_refs", []))
        target_inv_refs = set(target.metadata.get("invoice_refs", []))

        if target.type == EntityType.INVOICE and target.section:
            if target.section in source_inv_refs or target.metadata.get("invoice_number") in source_inv_refs:
                matched_refs.append(f"INV-{target.section}")

        if source.type == EntityType.INVOICE and source.section:
            if source.section in target_inv_refs or source.metadata.get("invoice_number") in target_inv_refs:
                matched_refs.append(f"INV-{source.section}")

        # Check VO-to-VO or INV-to-INV matches
        vo_matches = source_vo_refs & target_vo_refs
        matched_refs.extend([f"VO-{r}" for r in vo_matches])

        inv_matches = source_inv_refs & target_inv_refs
        matched_refs.extend([f"INV-{r}" for r in inv_matches])

        if not matched_refs:
            return None

        return self.build_evidence(
            EvidenceType.CLAUSE_REFERENCE,
            1.0,
            0.20,
            metadata={"matched_references": matched_refs},
        )

    def _check_date_proximity(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check if dates are within proximity threshold."""
        source_date = source.metadata.get("date")
        target_date = target.metadata.get("date")

        if not source_date or not target_date:
            return None

        try:
            # Parse dates if strings
            if isinstance(source_date, str):
                source_dt = datetime.fromisoformat(source_date.replace('/', '-'))
            else:
                source_dt = source_date

            if isinstance(target_date, str):
                target_dt = datetime.fromisoformat(target_date.replace('/', '-'))
            else:
                target_dt = target_date

            # Calculate day difference
            day_diff = abs((source_dt - target_dt).days)
            max_days = self._config.settings.get("date_proximity_days", 30)

            if day_diff > max_days:
                return None

            # Score inversely proportional to distance
            score = 1.0 - (day_diff / max_days) * 0.5

            return self.build_evidence(
                EvidenceType.DATE_PROXIMITY,
                score,
                0.15,
                source_text=source_dt.isoformat() if hasattr(source_dt, 'isoformat') else str(source_dt),
                target_text=target_dt.isoformat() if hasattr(target_dt, 'isoformat') else str(target_dt),
                metadata={"day_difference": day_diff},
            )

        except (ValueError, TypeError, AttributeError):
            return None

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _determine_link_type(
        self,
        source_type: EntityType,
        target_type: EntityType,
    ) -> Optional[LinkType]:
        """Determine the appropriate link type for entity type pair."""
        link_map = {
            # Cost to Payment
            (EntityType.COST_ITEM, EntityType.PAYMENT_CERT): LinkType.PAID_BY,
            (EntityType.PAYMENT_CERT, EntityType.COST_ITEM): LinkType.PAYS_FOR,
            # Cost to Variation
            (EntityType.COST_ITEM, EntityType.VARIATION_ORDER): LinkType.VARIED_BY,
            (EntityType.VARIATION_ORDER, EntityType.COST_ITEM): LinkType.VARIES,
            # Cost to Invoice
            (EntityType.COST_ITEM, EntityType.INVOICE): LinkType.INVOICED_BY,
            (EntityType.INVOICE, EntityType.COST_ITEM): LinkType.INVOICES,
            # Payment to Variation
            (EntityType.PAYMENT_CERT, EntityType.VARIATION_ORDER): LinkType.REFERENCES,
            (EntityType.VARIATION_ORDER, EntityType.PAYMENT_CERT): LinkType.REFERENCED_BY,
            # Payment to Invoice
            (EntityType.PAYMENT_CERT, EntityType.INVOICE): LinkType.REFERENCES,
            (EntityType.INVOICE, EntityType.PAYMENT_CERT): LinkType.REFERENCED_BY,
            # Variation to Invoice
            (EntityType.VARIATION_ORDER, EntityType.INVOICE): LinkType.INVOICED_BY,
            (EntityType.INVOICE, EntityType.VARIATION_ORDER): LinkType.INVOICES,
        }
        return link_map.get((source_type, target_type))

    def _extract_amounts(self, text: str) -> List[float]:
        """Extract monetary amounts from text."""
        # Pattern for amounts with optional currency symbols and commas
        pattern = r'(?:[$£€¥]|USD|GBP|EUR|SAR|AED)?\s*([0-9]{1,3}(?:,?[0-9]{3})*(?:\.[0-9]{2})?)'

        amounts: List[float] = []
        for match in re.finditer(pattern, text):
            try:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                if amount >= 100:  # Filter out small numbers that aren't amounts
                    amounts.append(amount)
            except ValueError:
                continue

        return amounts

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text."""
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',     # YYYY-MM-DD (must come first)
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',     # DD/MM/YYYY or MM/DD/YYYY (4-digit year)
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',  # DD Month YYYY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_cost_codes(self, text: str) -> List[str]:
        """Extract cost codes from text."""
        codes: List[str] = []

        for code_type, pattern in COST_CODE_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            codes.extend(matches)

        return list(set(codes))

    def _extract_commercial_references(self, text: str) -> Dict[str, List[str]]:
        """Extract commercial document references from text."""
        refs: Dict[str, List[str]] = {
            "variation": [],
            "invoice": [],
            "payment": [],
            "po": [],
        }

        # Variation references
        vo_pattern = r'(?:VO|Variation|Change\s*Order)\s*(?:No\.?|#)\s*([A-Z0-9-]+)'
        refs["variation"] = re.findall(vo_pattern, text, re.IGNORECASE)

        # Invoice references
        inv_pattern = r'(?:Invoice|INV|Bill)\s*(?:No\.?|#)\s*([A-Z0-9-]+)'
        refs["invoice"] = re.findall(inv_pattern, text, re.IGNORECASE)

        # Payment references
        pay_pattern = r'(?:IPC|Payment|PC)\s*(?:No\.?|#)\s*([A-Z0-9-]+)'
        refs["payment"] = re.findall(pay_pattern, text, re.IGNORECASE)

        # PO references
        po_pattern = r'(?:PO|Purchase\s*Order)\s*(?:No\.?|#)\s*([A-Z0-9-]+)'
        refs["po"] = re.findall(po_pattern, text, re.IGNORECASE)

        return refs

    def _extract_status(self, text: str) -> Optional[str]:
        """Extract status from text."""
        status_keywords = {
            "approved": ["approved", "accepted", "confirmed"],
            "pending": ["pending", "awaiting", "under review", "in progress"],
            "rejected": ["rejected", "declined", "refused"],
            "draft": ["draft", "provisional"],
            "final": ["final", "issued", "certified"],
        }

        text_lower = text.lower()
        for status, keywords in status_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return status

        return None

    def _get_domain_keywords(self) -> Set[str]:
        """Get all domain-specific keywords for matching."""
        keywords: Set[str] = set()
        for keyword_set in COMMERCIAL_KEYWORDS.values():
            keywords.update(keyword_set)

        return keywords
