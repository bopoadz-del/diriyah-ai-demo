"""Abstract base class for all linking packs in the ULE system."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from backend.reasoning.models import (
    Entity,
    EntityType,
    Evidence,
    EvidenceType,
    Link,
    LinkType,
    PackConfig,
)

logger = logging.getLogger(__name__)


class BasePack(ABC):
    """
    Abstract base class for domain-specific linking packs.

    Each pack implements entity extraction and matching logic for a specific
    domain (construction, commercial, etc.). Packs combine rule-based matching
    with semantic similarity for robust document linking.
    """

    def __init__(self, config: Optional[PackConfig] = None) -> None:
        """
        Initialize the pack with optional configuration.

        Args:
            config: Pack configuration. If None, uses default config from get_default_config().
        """
        self._config = config or self.get_default_config()
        self._entity_cache: Dict[str, Entity] = {}
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._keyword_index: Dict[str, Set[str]] = {}

        logger.info(
            "Initialized pack %s v%s with threshold %.2f",
            self._config.name,
            self._config.version,
            self._config.confidence_threshold,
        )

    @property
    def name(self) -> str:
        """Get the pack name."""
        return self._config.name

    @property
    def config(self) -> PackConfig:
        """Get the pack configuration."""
        return self._config

    @property
    def entity_types(self) -> List[EntityType]:
        """Get entity types this pack handles."""
        return self._config.entity_types

    @property
    def link_types(self) -> List[LinkType]:
        """Get link types this pack can create."""
        return self._config.link_types

    @classmethod
    @abstractmethod
    def get_default_config(cls) -> PackConfig:
        """
        Return the default configuration for this pack.

        Subclasses must implement this to provide their default settings.
        """
        pass

    @abstractmethod
    def extract_entities(
        self,
        content: str,
        document_id: str,
        document_name: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Entity]:
        """
        Extract entities from document content.

        Args:
            content: The document text content.
            document_id: Unique identifier for the document.
            document_name: Human-readable document name.
            document_type: Type of document (boq, specification, contract, drawing).
            metadata: Additional document metadata.

        Returns:
            List of extracted entities.
        """
        pass

    @abstractmethod
    def match_entities(
        self,
        source_entities: List[Entity],
        target_entities: List[Entity],
        embeddings: Optional[Dict[str, np.ndarray]] = None,
    ) -> List[Tuple[Entity, Entity, LinkType, float, List[Evidence]]]:
        """
        Find matching entity pairs with link type, confidence, and evidence.

        Args:
            source_entities: Entities to match from.
            target_entities: Entities to match to.
            embeddings: Pre-computed embeddings for entities.

        Returns:
            List of tuples: (source, target, link_type, confidence, evidence_list)
        """
        pass

    @abstractmethod
    def calculate_confidence(
        self,
        source: Entity,
        target: Entity,
        evidence: List[Evidence],
    ) -> float:
        """
        Calculate overall confidence score from evidence.

        Args:
            source: Source entity.
            target: Target entity.
            evidence: List of evidence items.

        Returns:
            Confidence score between 0 and 1.
        """
        pass

    def create_link(
        self,
        source: Entity,
        target: Entity,
        link_type: LinkType,
        confidence: float,
        evidence: List[Evidence],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Link:
        """
        Create a Link object from matched entities.

        Args:
            source: Source entity.
            target: Target entity.
            link_type: Type of link relationship.
            confidence: Confidence score.
            evidence: Supporting evidence.
            metadata: Additional link metadata.

        Returns:
            Configured Link object.
        """
        return Link(
            source=source,
            target=target,
            link_type=link_type,
            confidence=confidence,
            evidence=evidence,
            pack_name=self.name,
            metadata=metadata or {},
        )

    def should_link(self, source: Entity, target: Entity) -> bool:
        """
        Determine if two entities should potentially be linked.

        Override in subclasses for domain-specific filtering.

        Args:
            source: Source entity.
            target: Target entity.

        Returns:
            True if entities should be considered for linking.
        """
        # Don't link entity to itself
        if source.id == target.id:
            return False

        # Don't link same document unless different sections
        if (
            source.document_id
            and source.document_id == target.document_id
            and source.section == target.section
        ):
            return False

        return True

    # -------------------------------------------------------------------------
    # Utility methods for subclasses
    # -------------------------------------------------------------------------

    def compute_keyword_match(
        self,
        source: Entity,
        target: Entity,
        keywords: Optional[Set[str]] = None,
    ) -> Tuple[float, List[str]]:
        """
        Compute keyword overlap between two entities.

        Args:
            source: Source entity.
            target: Target entity.
            keywords: Optional set of domain-specific keywords to prioritize.

        Returns:
            Tuple of (match_score, matched_keywords).
        """
        source_words = self._tokenize(source.text)
        target_words = self._tokenize(target.text)

        if not source_words or not target_words:
            return 0.0, []

        # Find common words
        common = source_words & target_words

        # Prioritize domain keywords if provided
        if keywords:
            domain_matches = common & keywords
            domain_weight = len(domain_matches) / max(len(keywords), 1)
        else:
            domain_weight = 0.0
            domain_matches = set()

        # Calculate Jaccard similarity
        union = source_words | target_words
        jaccard = len(common) / len(union) if union else 0.0

        # Combined score (domain keywords weighted higher)
        score = (jaccard * 0.4) + (domain_weight * 0.6) if keywords else jaccard

        matched = list(domain_matches if domain_matches else common)
        return min(score, 1.0), matched[:10]  # Limit to top 10 matches

    def compute_semantic_similarity(
        self,
        source_embedding: np.ndarray,
        target_embedding: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            source_embedding: Source entity embedding.
            target_embedding: Target entity embedding.

        Returns:
            Cosine similarity score between 0 and 1.
        """
        if source_embedding is None or target_embedding is None:
            return 0.0

        # Normalize vectors
        source_norm = np.linalg.norm(source_embedding)
        target_norm = np.linalg.norm(target_embedding)

        if source_norm == 0 or target_norm == 0:
            return 0.0

        source_normalized = source_embedding / source_norm
        target_normalized = target_embedding / target_norm

        # Cosine similarity
        similarity = float(np.dot(source_normalized, target_normalized))

        # Ensure result is in [0, 1]
        return max(0.0, min(1.0, similarity))

    def extract_codes(self, text: str, pattern: str) -> List[str]:
        """
        Extract codes matching a regex pattern from text.

        Args:
            text: Text to search.
            pattern: Regex pattern with groups.

        Returns:
            List of matched codes.
        """
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Flatten if groups returned tuples
            if matches and isinstance(matches[0], tuple):
                return [m[0] for m in matches if m[0]]
            return matches
        except re.error:
            logger.warning("Invalid regex pattern: %s", pattern)
            return []

    def extract_references(self, text: str) -> Dict[str, List[str]]:
        """
        Extract common reference patterns from text.

        Args:
            text: Text to search.

        Returns:
            Dictionary of reference type to list of references.
        """
        references: Dict[str, List[str]] = {
            "drawing": [],
            "specification": [],
            "clause": [],
            "section": [],
        }

        # Drawing references (e.g., DWG-001, A-101, SK-001)
        drawing_pattern = r'\b([A-Z]{1,3}[-/]?\d{2,4}(?:[-/][A-Z]?\d{1,3})?)\b'
        references["drawing"] = self.extract_codes(text, drawing_pattern)

        # Specification section (e.g., Section 03300, Spec 05120)
        spec_pattern = r'\b(?:Section|Spec|Specification)\s*(\d{5})\b'
        references["specification"] = self.extract_codes(text, spec_pattern)

        # Contract clause (e.g., Clause 4.1, Article 5.2.3)
        clause_pattern = r'\b(?:Clause|Article|Section)\s*(\d+(?:\.\d+)*)\b'
        references["clause"] = self.extract_codes(text, clause_pattern)

        # Generic section references
        section_pattern = r'\b(?:Section|Part)\s*(\d+(?:\.\d+)*)\b'
        references["section"] = self.extract_codes(text, section_pattern)

        return references

    def build_evidence(
        self,
        evidence_type: EvidenceType,
        value: Any,
        weight: float,
        source_text: Optional[str] = None,
        target_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Evidence:
        """
        Build an Evidence object with the given parameters.

        Args:
            evidence_type: Type of evidence.
            value: The matched value or score.
            weight: Weight in confidence calculation.
            source_text: Source text that matched.
            target_text: Target text that matched.
            metadata: Additional metadata.

        Returns:
            Configured Evidence object.
        """
        return Evidence(
            type=evidence_type,
            value=value,
            weight=weight,
            source_text=source_text,
            target_text=target_text,
            metadata=metadata or {},
        )

    def _tokenize(self, text: str) -> Set[str]:
        """
        Tokenize text into a set of normalized words.

        Args:
            text: Text to tokenize.

        Returns:
            Set of lowercase words (min length 2).
        """
        if not text:
            return set()

        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter short words and common stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'as', 'per', 'all',
        }

        return {w for w in words if len(w) >= 2 and w not in stopwords}

    def cache_entity(self, entity: Entity) -> None:
        """Cache an entity for later retrieval."""
        self._entity_cache[entity.id] = entity

    def get_cached_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve a cached entity by ID."""
        return self._entity_cache.get(entity_id)

    def cache_embedding(self, entity_id: str, embedding: np.ndarray) -> None:
        """Cache an embedding for an entity."""
        self._embedding_cache[entity_id] = embedding

    def get_cached_embedding(self, entity_id: str) -> Optional[np.ndarray]:
        """Retrieve a cached embedding by entity ID."""
        return self._embedding_cache.get(entity_id)

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._entity_cache.clear()
        self._embedding_cache.clear()
        self._keyword_index.clear()
