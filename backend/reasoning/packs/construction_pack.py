"""Construction Pack for linking BOQ, Specifications, Contracts, and Drawings."""

from __future__ import annotations

import logging
import re
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


# CSI MasterFormat Division codes and their descriptions
CSI_DIVISIONS: Dict[str, str] = {
    "00": "Procurement and Contracting Requirements",
    "01": "General Requirements",
    "02": "Existing Conditions",
    "03": "Concrete",
    "04": "Masonry",
    "05": "Metals",
    "06": "Wood, Plastics, and Composites",
    "07": "Thermal and Moisture Protection",
    "08": "Openings",
    "09": "Finishes",
    "10": "Specialties",
    "11": "Equipment",
    "12": "Furnishings",
    "13": "Special Construction",
    "14": "Conveying Equipment",
    "21": "Fire Suppression",
    "22": "Plumbing",
    "23": "Heating, Ventilating, and Air Conditioning",
    "25": "Integrated Automation",
    "26": "Electrical",
    "27": "Communications",
    "28": "Electronic Safety and Security",
    "31": "Earthwork",
    "32": "Exterior Improvements",
    "33": "Utilities",
    "34": "Transportation",
    "35": "Waterway and Marine Construction",
    "40": "Process Integration",
    "41": "Material Processing and Handling Equipment",
    "42": "Process Heating, Cooling, and Drying Equipment",
    "43": "Process Gas and Liquid Handling",
    "44": "Pollution Control Equipment",
    "45": "Industry-Specific Manufacturing Equipment",
    "46": "Water and Wastewater Equipment",
    "48": "Electrical Power Generation",
}

# Common construction materials and their variations
MATERIAL_KEYWORDS: Dict[str, Set[str]] = {
    "concrete": {"concrete", "cement", "c20", "c25", "c30", "c35", "c40", "c45", "c50", "rcc", "pcc", "precast"},
    "steel": {"steel", "rebar", "reinforcement", "structural", "mild", "high-tensile", "stainless", "galvanized"},
    "masonry": {"brick", "block", "masonry", "mortar", "cmu", "aac", "clay"},
    "timber": {"timber", "wood", "plywood", "mdf", "hardwood", "softwood", "lumber"},
    "waterproofing": {"waterproofing", "membrane", "bitumen", "epdm", "tpo", "pvc", "sealant"},
    "insulation": {"insulation", "thermal", "acoustic", "rockwool", "glasswool", "xps", "eps", "pir"},
    "finishes": {"paint", "plaster", "render", "tiles", "flooring", "ceiling", "gypsum"},
    "mechanical": {"hvac", "ductwork", "piping", "plumbing", "drainage", "chiller", "ahu"},
    "electrical": {"electrical", "cable", "conduit", "switchgear", "panel", "lighting", "transformer"},
}


class ConstructionPack(BasePack):
    """
    Construction Pack for linking BOQ items, Specifications, Contract clauses, and Drawings.

    This pack specializes in:
    - BOQ Item ↔ Specification Section linking via CSI codes and material matching
    - Specification ↔ Contract Clause linking via compliance references
    - BOQ/Spec ↔ Drawing linking via drawing number references
    """

    @classmethod
    def get_default_config(cls) -> PackConfig:
        """Return default configuration for ConstructionPack."""
        return PackConfig(
            name="ConstructionPack",
            version="1.0.0",
            description="Links BOQ items to specifications, contracts, and drawings",
            entity_types=[
                EntityType.BOQ_ITEM,
                EntityType.SPEC_SECTION,
                EntityType.CONTRACT_CLAUSE,
                EntityType.DRAWING_REF,
            ],
            link_types=[
                LinkType.SPECIFIES,
                LinkType.SPECIFIED_BY,
                LinkType.REFERENCES,
                LinkType.REFERENCED_BY,
                LinkType.COMPLIES_WITH,
                LinkType.GOVERNS,
                LinkType.DEPICTS,
                LinkType.DEPICTED_IN,
            ],
            confidence_threshold=0.75,
            semantic_weight=0.6,
            keyword_weight=0.4,
            settings={
                "csi_match_weight": 0.35,
                "material_match_weight": 0.25,
                "drawing_ref_weight": 0.20,
                "quantity_match_weight": 0.10,
                "min_keyword_overlap": 0.15,
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
        Extract construction entities from document content.

        Handles BOQ items, specification sections, contract clauses, and drawing references.
        """
        metadata = metadata or {}
        entities: List[Entity] = []

        doc_type_lower = document_type.lower()

        if doc_type_lower in ("boq", "bill of quantities", "quantities"):
            entities.extend(self._extract_boq_items(content, document_id, document_name, metadata))
        elif doc_type_lower in ("specification", "spec", "specs"):
            entities.extend(self._extract_spec_sections(content, document_id, document_name, metadata))
        elif doc_type_lower in ("contract", "agreement"):
            entities.extend(self._extract_contract_clauses(content, document_id, document_name, metadata))
        elif doc_type_lower in ("drawing", "dwg", "cad"):
            entities.extend(self._extract_drawing_refs(content, document_id, document_name, metadata))
        else:
            # Try to extract all types from generic document
            entities.extend(self._extract_boq_items(content, document_id, document_name, metadata))
            entities.extend(self._extract_spec_sections(content, document_id, document_name, metadata))
            entities.extend(self._extract_drawing_refs(content, document_id, document_name, metadata))

        logger.info(
            "Extracted %d entities from %s (%s)",
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
        Find matching entity pairs with construction-specific logic.

        Matches are based on:
        - CSI code alignment
        - Material/keyword overlap
        - Drawing references
        - Semantic similarity (if embeddings provided)
        """
        embeddings = embeddings or {}
        matches: List[Tuple[Entity, Entity, LinkType, float, List[Evidence]]] = []

        for source in source_entities:
            for target in target_entities:
                if not self.should_link(source, target):
                    continue

                # Determine link type based on entity types
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
            "Found %d matches from %d source x %d target entities",
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

        Uses weighted combination of evidence scores.
        """
        if not evidence:
            return 0.0

        total_weight = sum(e.weight for e in evidence)
        if total_weight == 0:
            return 0.0

        # Weighted average of evidence values
        weighted_sum = sum(
            float(e.value) * e.weight if isinstance(e.value, (int, float)) else e.weight * 0.8
            for e in evidence
        )

        base_confidence = weighted_sum / total_weight

        # Boost confidence for strong CSI code matches
        csi_evidence = [e for e in evidence if e.type == EvidenceType.CSI_CODE_MATCH]
        if csi_evidence:
            base_confidence = min(1.0, base_confidence + 0.1)

        # Boost for multiple evidence types
        evidence_types = {e.type for e in evidence}
        if len(evidence_types) >= 3:
            base_confidence = min(1.0, base_confidence + 0.05)

        return round(base_confidence, 3)

    def should_link(self, source: Entity, target: Entity) -> bool:
        """Check if entities should be considered for linking."""
        if not super().should_link(source, target):
            return False

        # Define valid entity type combinations
        valid_combinations = {
            (EntityType.BOQ_ITEM, EntityType.SPEC_SECTION),
            (EntityType.BOQ_ITEM, EntityType.DRAWING_REF),
            (EntityType.BOQ_ITEM, EntityType.CONTRACT_CLAUSE),
            (EntityType.SPEC_SECTION, EntityType.BOQ_ITEM),
            (EntityType.SPEC_SECTION, EntityType.CONTRACT_CLAUSE),
            (EntityType.SPEC_SECTION, EntityType.DRAWING_REF),
            (EntityType.CONTRACT_CLAUSE, EntityType.SPEC_SECTION),
            (EntityType.CONTRACT_CLAUSE, EntityType.BOQ_ITEM),
            (EntityType.DRAWING_REF, EntityType.BOQ_ITEM),
            (EntityType.DRAWING_REF, EntityType.SPEC_SECTION),
        }

        return (source.type, target.type) in valid_combinations

    # -------------------------------------------------------------------------
    # Entity extraction methods
    # -------------------------------------------------------------------------

    def _extract_boq_items(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract BOQ items from content."""
        entities: List[Entity] = []
        lines = content.split('\n')

        # Pattern for BOQ items (item number, description, quantity, unit)
        # Handles formats like: "1.1 Description - 500 m3" or "Item 1.1 Description 500 m3"
        boq_pattern = r'^[\s]*(?:Item\s+)?([A-Z]?\d+(?:\.\d+)*)\s+(.+?)(?:\s*[-–]\s*|\s+)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(m[²³]?|m2|m3|kg|ton|tons?|nr|nos|ls|set|pc|pcs|each|lm|sqm|cum)\s*$'

        for idx, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 10:
                continue

            match = re.match(boq_pattern, line, re.IGNORECASE)
            if match:
                item_id = match.group(1)
                description = match.group(2).strip()
                quantity = match.group(3)
                unit = match.group(4)

                # Extract CSI code if present in description
                csi_codes = self._extract_csi_codes(description)

                entity = Entity(
                    id=f"{document_id}-BOQ-{item_id}",
                    type=EntityType.BOQ_ITEM,
                    text=description,
                    document_id=document_id,
                    document_name=document_name,
                    page_number=None,
                    section=csi_codes[0] if csi_codes else None,
                    metadata={
                        "item_number": item_id,
                        "quantity": quantity,
                        "unit": unit,
                        "csi_codes": csi_codes,
                        "materials": self._identify_materials(description),
                        "line_number": idx + 1,
                        **metadata,
                    },
                )
                entities.append(entity)
                self.cache_entity(entity)

        # Also extract from structured patterns
        entities.extend(self._extract_structured_boq(content, document_id, document_name, metadata))

        return entities

    def _extract_structured_boq(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract BOQ items from table-like structures."""
        entities: List[Entity] = []

        # Pattern for structured BOQ (common in Excel exports)
        structured_pattern = r'(?:Item|Ref|No\.?)\s*[:.]?\s*([A-Z]?\d+(?:[.-]\d+)*)\s*[-:|]\s*(.+?)(?:\s*[-:|]\s*(?:Qty|Quantity)\s*[:.]?\s*(\d+(?:,\d{3})*(?:\.\d+)?))?'

        for match in re.finditer(structured_pattern, content, re.IGNORECASE | re.MULTILINE):
            item_id = match.group(1)
            description = match.group(2).strip()

            # Skip if already extracted
            entity_id = f"{document_id}-BOQ-{item_id}"
            if self.get_cached_entity(entity_id):
                continue

            csi_codes = self._extract_csi_codes(description)

            entity = Entity(
                id=entity_id,
                type=EntityType.BOQ_ITEM,
                text=description,
                document_id=document_id,
                document_name=document_name,
                section=csi_codes[0] if csi_codes else None,
                metadata={
                    "item_number": item_id,
                    "csi_codes": csi_codes,
                    "materials": self._identify_materials(description),
                    **metadata,
                },
            )
            entities.append(entity)
            self.cache_entity(entity)

        return entities

    def _extract_spec_sections(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract specification sections from content."""
        entities: List[Entity] = []

        # Pattern for specification sections (CSI format)
        section_pattern = r'(?:SECTION|Section)\s+(\d{5,6})\s*[-–—:]\s*([^\n]+)'

        for match in re.finditer(section_pattern, content):
            section_number = match.group(1)
            section_title = match.group(2).strip()

            # Get section content (text until next section)
            start_pos = match.end()
            next_section = re.search(r'(?:SECTION|Section)\s+\d{5,6}', content[start_pos:])
            end_pos = start_pos + next_section.start() if next_section else len(content)
            section_content = content[start_pos:end_pos].strip()[:500]  # Limit content length

            # Determine CSI division
            division = section_number[:2]
            division_name = CSI_DIVISIONS.get(division, "Unknown Division")

            entity = Entity(
                id=f"{document_id}-SPEC-{section_number}",
                type=EntityType.SPEC_SECTION,
                text=f"{section_title}. {section_content}",
                document_id=document_id,
                document_name=document_name,
                section=section_number,
                metadata={
                    "section_number": section_number,
                    "section_title": section_title,
                    "division": division,
                    "division_name": division_name,
                    "materials": self._identify_materials(section_title + " " + section_content),
                    "drawing_refs": self._extract_drawing_numbers(section_content),
                    **metadata,
                },
            )
            entities.append(entity)
            self.cache_entity(entity)

        # Also extract informal spec references
        informal_pattern = r'(?:Spec(?:ification)?|Technical\s+Requirement)\s*[:.]?\s*([A-Z]?\d+(?:[.-]\d+)*)\s*[-–—:]\s*([^\n]+)'

        for match in re.finditer(informal_pattern, content, re.IGNORECASE):
            ref_number = match.group(1)
            title = match.group(2).strip()

            entity_id = f"{document_id}-SPEC-{ref_number}"
            if self.get_cached_entity(entity_id):
                continue

            entity = Entity(
                id=entity_id,
                type=EntityType.SPEC_SECTION,
                text=title,
                document_id=document_id,
                document_name=document_name,
                section=ref_number,
                metadata={
                    "section_number": ref_number,
                    "section_title": title,
                    "materials": self._identify_materials(title),
                    **metadata,
                },
            )
            entities.append(entity)
            self.cache_entity(entity)

        return entities

    def _extract_contract_clauses(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract contract clauses from content."""
        entities: List[Entity] = []

        # Pattern for contract clauses
        clause_pattern = r'(?:Clause|Article|Section)\s+(\d+(?:\.\d+)*)\s*[-–—:.]?\s*([^\n]+)'

        for match in re.finditer(clause_pattern, content, re.IGNORECASE):
            clause_number = match.group(1)
            clause_title = match.group(2).strip()

            # Get clause content
            start_pos = match.end()
            next_clause = re.search(r'(?:Clause|Article|Section)\s+\d+(?:\.\d+)*', content[start_pos:], re.IGNORECASE)
            end_pos = start_pos + next_clause.start() if next_clause else min(start_pos + 1000, len(content))
            clause_content = content[start_pos:end_pos].strip()[:500]

            entity = Entity(
                id=f"{document_id}-CLAUSE-{clause_number}",
                type=EntityType.CONTRACT_CLAUSE,
                text=f"{clause_title}. {clause_content}",
                document_id=document_id,
                document_name=document_name,
                section=clause_number,
                metadata={
                    "clause_number": clause_number,
                    "clause_title": clause_title,
                    "spec_refs": self._extract_spec_references(clause_content),
                    **metadata,
                },
            )
            entities.append(entity)
            self.cache_entity(entity)

        return entities

    def _extract_drawing_refs(
        self,
        content: str,
        document_id: str,
        document_name: str,
        metadata: Dict[str, Any],
    ) -> List[Entity]:
        """Extract drawing references from content."""
        entities: List[Entity] = []

        # Drawing number patterns
        drawing_patterns = [
            r'\b([A-Z]{1,3}[-/]?\d{2,4}(?:[-/][A-Z]?\d{1,3})?)\b',  # A-101, SK-001, M-201-A
            r'\b(DWG[-/]?\d{3,6})\b',  # DWG-001234
            r'\b(DR[-/]?\d{3,6})\b',   # DR-001234
        ]

        seen_drawings: Set[str] = set()

        for pattern in drawing_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                drawing_number = match.group(1).upper()

                if drawing_number in seen_drawings:
                    continue
                seen_drawings.add(drawing_number)

                # Get surrounding context
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end].strip()

                # Determine drawing type from prefix
                drawing_type = self._determine_drawing_type(drawing_number)

                entity = Entity(
                    id=f"{document_id}-DWG-{drawing_number}",
                    type=EntityType.DRAWING_REF,
                    text=context,
                    document_id=document_id,
                    document_name=document_name,
                    section=drawing_number,
                    metadata={
                        "drawing_number": drawing_number,
                        "drawing_type": drawing_type,
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
        """Collect all evidence for a potential link."""
        evidence: List[Evidence] = []
        settings = self._config.settings

        # 1. CSI code matching
        csi_evidence = self._check_csi_match(source, target)
        if csi_evidence:
            csi_evidence.weight = settings.get("csi_match_weight", 0.35)
            evidence.append(csi_evidence)

        # 2. Material matching
        material_evidence = self._check_material_match(source, target)
        if material_evidence:
            material_evidence.weight = settings.get("material_match_weight", 0.25)
            evidence.append(material_evidence)

        # 3. Drawing reference matching
        drawing_evidence = self._check_drawing_reference(source, target)
        if drawing_evidence:
            drawing_evidence.weight = settings.get("drawing_ref_weight", 0.20)
            evidence.append(drawing_evidence)

        # 4. Keyword matching
        keyword_score, matched_keywords = self.compute_keyword_match(
            source, target, self._get_domain_keywords()
        )
        min_overlap = settings.get("min_keyword_overlap", 0.15)
        if keyword_score >= min_overlap and matched_keywords:
            evidence.append(
                self.build_evidence(
                    EvidenceType.KEYWORD_MATCH,
                    keyword_score,
                    self._config.keyword_weight,
                    source_text=source.text[:100],
                    target_text=target.text[:100],
                    metadata={"matched_keywords": matched_keywords},
                )
            )

        # 5. Semantic similarity
        source_emb = embeddings.get(source.id)
        target_emb = embeddings.get(target.id)
        if source_emb is not None and target_emb is not None:
            similarity = self.compute_semantic_similarity(source_emb, target_emb)
            if similarity >= 0.5:
                evidence.append(
                    self.build_evidence(
                        EvidenceType.SEMANTIC_SIMILARITY,
                        similarity,
                        self._config.semantic_weight,
                    )
                )

        return evidence

    def _check_csi_match(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check for CSI code matches between entities."""
        source_codes = set(source.metadata.get("csi_codes", []))
        if source.section:
            source_codes.add(source.section[:5] if len(source.section) >= 5 else source.section)

        target_codes = set(target.metadata.get("csi_codes", []))
        if target.section:
            target_codes.add(target.section[:5] if len(target.section) >= 5 else target.section)

        if not source_codes or not target_codes:
            return None

        # Check for exact or prefix matches
        matched_codes: List[str] = []

        for sc in source_codes:
            for tc in target_codes:
                # Exact match
                if sc == tc:
                    matched_codes.append(sc)
                # Division match (first 2 digits)
                elif sc[:2] == tc[:2]:
                    matched_codes.append(f"{sc[:2]}xxx")

        if not matched_codes:
            return None

        # Higher score for exact matches
        exact_matches = [c for c in matched_codes if 'x' not in c]
        score = 1.0 if exact_matches else 0.7

        return self.build_evidence(
            EvidenceType.CSI_CODE_MATCH,
            score,
            0.35,  # Will be overwritten
            source_text=", ".join(source_codes),
            target_text=", ".join(target_codes),
            metadata={"matched_codes": matched_codes},
        )

    def _check_material_match(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check for material matches between entities."""
        source_materials = set(source.metadata.get("materials", []))
        target_materials = set(target.metadata.get("materials", []))

        if not source_materials and not target_materials:
            # Try to identify from text
            source_materials = self._identify_materials(source.text)
            target_materials = self._identify_materials(target.text)

        if not source_materials or not target_materials:
            return None

        matched = source_materials & target_materials
        if not matched:
            return None

        # Score based on proportion of matches
        union = source_materials | target_materials
        score = len(matched) / len(union)

        return self.build_evidence(
            EvidenceType.MATERIAL_MATCH,
            score,
            0.25,  # Will be overwritten
            metadata={"matched_materials": list(matched)},
        )

    def _check_drawing_reference(self, source: Entity, target: Entity) -> Optional[Evidence]:
        """Check for drawing number references."""
        source_drawings = set(source.metadata.get("drawing_refs", []))
        target_drawings = set(target.metadata.get("drawing_refs", []))

        # Also check section field for drawing entities
        if source.type == EntityType.DRAWING_REF and source.section:
            source_drawings.add(source.section)
        if target.type == EntityType.DRAWING_REF and target.section:
            target_drawings.add(target.section)

        # Extract drawing numbers from text if not in metadata
        if not source_drawings:
            source_drawings = set(self._extract_drawing_numbers(source.text))
        if not target_drawings:
            target_drawings = set(self._extract_drawing_numbers(target.text))

        if not source_drawings or not target_drawings:
            return None

        matched = source_drawings & target_drawings
        if not matched:
            return None

        return self.build_evidence(
            EvidenceType.DRAWING_REFERENCE,
            1.0,
            0.20,  # Will be overwritten
            metadata={"matched_drawings": list(matched)},
        )

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
            (EntityType.BOQ_ITEM, EntityType.SPEC_SECTION): LinkType.SPECIFIED_BY,
            (EntityType.SPEC_SECTION, EntityType.BOQ_ITEM): LinkType.SPECIFIES,
            (EntityType.BOQ_ITEM, EntityType.DRAWING_REF): LinkType.DEPICTED_IN,
            (EntityType.DRAWING_REF, EntityType.BOQ_ITEM): LinkType.DEPICTS,
            (EntityType.BOQ_ITEM, EntityType.CONTRACT_CLAUSE): LinkType.COMPLIES_WITH,
            (EntityType.CONTRACT_CLAUSE, EntityType.BOQ_ITEM): LinkType.GOVERNS,
            (EntityType.SPEC_SECTION, EntityType.CONTRACT_CLAUSE): LinkType.COMPLIES_WITH,
            (EntityType.CONTRACT_CLAUSE, EntityType.SPEC_SECTION): LinkType.GOVERNS,
            (EntityType.SPEC_SECTION, EntityType.DRAWING_REF): LinkType.REFERENCES,
            (EntityType.DRAWING_REF, EntityType.SPEC_SECTION): LinkType.REFERENCED_BY,
        }
        return link_map.get((source_type, target_type))

    def _extract_csi_codes(self, text: str) -> List[str]:
        """Extract CSI MasterFormat codes from text."""
        # Pattern for 5 or 6 digit CSI codes
        pattern = r'\b(\d{5,6})\b'
        codes = re.findall(pattern, text)

        # Filter to valid CSI divisions
        valid_codes = []
        for code in codes:
            division = code[:2]
            if division in CSI_DIVISIONS:
                valid_codes.append(code)

        return valid_codes

    def _extract_spec_references(self, text: str) -> List[str]:
        """Extract specification references from text."""
        patterns = [
            r'(?:Section|Spec)\s*(\d{5,6})',
            r'(?:refer(?:ence)?|see)\s+(?:Section|Spec)\s*(\d{5,6})',
        ]

        refs = []
        for pattern in patterns:
            refs.extend(re.findall(pattern, text, re.IGNORECASE))

        return list(set(refs))

    def _extract_drawing_numbers(self, text: str) -> List[str]:
        """Extract drawing numbers from text."""
        patterns = [
            r'\b([A-Z]{1,3}[-/]?\d{2,4}(?:[-/][A-Z]?\d{1,3})?)\b',
            r'\b(DWG[-/]?\d{3,6})\b',
        ]

        drawings = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            drawings.extend([m.upper() for m in matches])

        return list(set(drawings))

    def _identify_materials(self, text: str) -> Set[str]:
        """Identify materials mentioned in text."""
        text_lower = text.lower()
        found_materials: Set[str] = set()

        for material_category, keywords in MATERIAL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found_materials.add(material_category)

        return found_materials

    def _determine_drawing_type(self, drawing_number: str) -> str:
        """Determine drawing type from number prefix."""
        prefix = drawing_number.split('-')[0].upper() if '-' in drawing_number else drawing_number[:1].upper()

        type_map = {
            'A': 'Architectural',
            'S': 'Structural',
            'M': 'Mechanical',
            'E': 'Electrical',
            'P': 'Plumbing',
            'C': 'Civil',
            'L': 'Landscape',
            'SK': 'Sketch',
            'DWG': 'General',
            'DR': 'General',
        }

        return type_map.get(prefix, 'Unknown')

    def _get_domain_keywords(self) -> Set[str]:
        """Get all domain-specific keywords for matching."""
        keywords: Set[str] = set()
        for material_keywords in MATERIAL_KEYWORDS.values():
            keywords.update(material_keywords)

        # Add additional construction keywords
        keywords.update({
            'foundation', 'slab', 'beam', 'column', 'wall', 'floor', 'roof',
            'door', 'window', 'facade', 'cladding', 'partition', 'ceiling',
            'duct', 'pipe', 'cable', 'tray', 'conduit', 'fitting', 'fixture',
            'supply', 'install', 'provide', 'construct', 'erect', 'demolish',
        })

        return keywords
