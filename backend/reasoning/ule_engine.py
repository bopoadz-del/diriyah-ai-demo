"""Universal Linking Engine (ULE) - Main orchestration engine for document linking."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

import numpy as np

from backend.reasoning.schemas import (
    DocumentInput,
    Entity,
    EntityType,
    Evidence,
    EvidenceResponse,
    EvidenceType,
    Link,
    LinkResult,
    LinkType,
    PackConfig,
)
from backend.reasoning.packs.base_pack import BasePack

logger = logging.getLogger(__name__)


# Optional dependencies for embeddings
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment]

try:
    import faiss
except ImportError:
    faiss = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment]

try:
    import os
    if OpenAI is not None:
        _openai_api_key = os.getenv("OPENAI_API_KEY")
        _openai_client = OpenAI(api_key=_openai_api_key) if _openai_api_key else None
    else:
        _openai_client = None
except Exception:
    _openai_client = None


class ULEEngine:
    """
    Universal Linking Engine for automatic construction document linking.

    The ULE manages domain-specific packs and orchestrates the linking process:
    1. Documents are processed by registered packs to extract entities
    2. Entities are embedded using sentence transformers or OpenAI
    3. Links are discovered through hybrid rule-based + semantic matching
    4. Results include confidence scores and evidence trails

    Example usage:
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())
        engine.register_pack(CommercialPack())

        result = await engine.process_document(document)
        links = await engine.find_links(document_id="DOC-001")
    """

    def __init__(
        self,
        default_confidence_threshold: float = 0.75,
        embedding_model: str = "all-MiniLM-L6-v2",
        use_openai_embeddings: bool = False,
    ) -> None:
        """
        Initialize the ULE Engine.

        Args:
            default_confidence_threshold: Minimum confidence for links (0-1).
            embedding_model: Sentence transformer model name.
            use_openai_embeddings: Use OpenAI embeddings instead of local model.
        """
        self._packs: Dict[str, BasePack] = {}
        self._entities: Dict[str, Entity] = {}
        self._links: Dict[UUID, Link] = {}
        self._document_entities: Dict[str, List[str]] = {}  # doc_id -> entity_ids
        self._embeddings: Dict[str, np.ndarray] = {}
        self._default_threshold = default_confidence_threshold

        # Initialize embedding model
        self._embedding_model: Optional[SentenceTransformer] = None
        self._embedding_dimension: int = 384  # Default for MiniLM
        self._use_openai = use_openai_embeddings and _openai_client is not None

        if not self._use_openai:
            self._initialize_local_embeddings(embedding_model)
        else:
            self._embedding_dimension = 1536  # OpenAI ada-002

        # Initialize FAISS index for fast similarity search
        self._faiss_index = None
        self._faiss_id_map: Dict[int, str] = {}
        self._initialize_faiss_index()

        logger.info(
            "ULE Engine initialized: threshold=%.2f, embeddings=%s, faiss=%s",
            self._default_threshold,
            "openai" if self._use_openai else ("local" if self._embedding_model else "disabled"),
            self._faiss_index is not None,
        )

    def _initialize_local_embeddings(self, model_name: str) -> None:
        """Initialize local sentence transformer model."""
        if SentenceTransformer is None:
            logger.warning("sentence-transformers not installed; embeddings disabled")
            return

        try:
            self._embedding_model = SentenceTransformer(model_name)
            self._embedding_dimension = self._embedding_model.get_sentence_embedding_dimension()
            logger.info("Loaded embedding model: %s (dim=%d)", model_name, self._embedding_dimension)
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", e)
            self._embedding_model = None

    def _initialize_faiss_index(self) -> None:
        """Initialize FAISS index for vector similarity search."""
        if faiss is None:
            logger.warning("faiss-cpu not installed; using brute-force similarity")
            return

        try:
            self._faiss_index = faiss.IndexFlatIP(self._embedding_dimension)
            logger.info("FAISS index initialized with dimension %d", self._embedding_dimension)
        except Exception as e:
            logger.warning("Failed to initialize FAISS: %s", e)
            self._faiss_index = None

    # -------------------------------------------------------------------------
    # Pack management
    # -------------------------------------------------------------------------

    def register_pack(self, pack: BasePack) -> None:
        """
        Register a pack with the engine.

        Args:
            pack: Pack instance to register.
        """
        if pack.name in self._packs:
            logger.warning("Pack %s already registered; replacing", pack.name)

        self._packs[pack.name] = pack
        logger.info(
            "Registered pack: %s v%s (entities: %s)",
            pack.name,
            pack.config.version,
            [e.value for e in pack.entity_types],
        )

    def unregister_pack(self, pack_name: str) -> bool:
        """
        Unregister a pack from the engine.

        Args:
            pack_name: Name of the pack to remove.

        Returns:
            True if pack was removed, False if not found.
        """
        if pack_name in self._packs:
            del self._packs[pack_name]
            logger.info("Unregistered pack: %s", pack_name)
            return True
        return False

    def get_pack(self, pack_name: str) -> Optional[BasePack]:
        """Get a registered pack by name."""
        return self._packs.get(pack_name)

    def list_packs(self) -> List[PackConfig]:
        """List all registered packs and their configurations."""
        return [pack.config for pack in self._packs.values()]

    # -------------------------------------------------------------------------
    # Document processing
    # -------------------------------------------------------------------------

    async def process_document(
        self,
        document: DocumentInput,
        packs: Optional[List[str]] = None,
    ) -> LinkResult:
        """
        Process a document to extract entities and find links.

        Args:
            document: Document to process.
            packs: Specific pack names to use (None = all registered packs).

        Returns:
            LinkResult with extracted entities and discovered links.
        """
        start_time = time.time()

        # Determine which packs to use
        active_packs = self._get_active_packs(packs)
        if not active_packs:
            logger.warning("No packs available for processing")
            return LinkResult(
                document_id=document.document_id,
                packs_used=[],
                metadata={"error": "No packs registered"},
            )

        # Extract entities from each pack
        all_entities: List[Entity] = []
        for pack in active_packs:
            try:
                entities = pack.extract_entities(
                    content=document.content,
                    document_id=document.document_id,
                    document_name=document.document_name,
                    document_type=document.document_type,
                    metadata=document.metadata,
                )
                all_entities.extend(entities)
            except Exception as e:
                logger.exception("Pack %s failed to extract entities: %s", pack.name, e)

        # Store entities
        entity_ids = []
        for entity in all_entities:
            self._entities[entity.id] = entity
            entity_ids.append(entity.id)

        self._document_entities[document.document_id] = entity_ids

        # Compute embeddings for new entities
        await self._compute_embeddings(all_entities)

        # Find links within this document and with existing entities
        links = await self._find_links_for_entities(all_entities, active_packs)

        # Store links
        for link in links:
            self._links[link.id] = link

        processing_time = (time.time() - start_time) * 1000

        return LinkResult(
            document_id=document.document_id,
            links=links,
            total_entities_processed=len(all_entities),
            total_links_found=len(links),
            processing_time_ms=processing_time,
            packs_used=[p.name for p in active_packs],
            confidence_threshold=self._default_threshold,
            metadata={
                "entity_types": list({e.type.value for e in all_entities}),
            },
        )

    async def find_links(
        self,
        document_id: Optional[str] = None,
        query_text: Optional[str] = None,
        entity_types: Optional[List[EntityType]] = None,
        link_types: Optional[List[LinkType]] = None,
        packs: Optional[List[str]] = None,
        confidence_threshold: Optional[float] = None,
        max_links: int = 100,
    ) -> LinkResult:
        """
        Find links for a document or query.

        Args:
            document_id: Find links involving this document's entities.
            query_text: Find links for entities matching this query.
            entity_types: Filter results to these entity types.
            link_types: Filter results to these link types.
            packs: Use only these packs.
            confidence_threshold: Override default threshold.
            max_links: Maximum number of links to return.

        Returns:
            LinkResult with matching links.
        """
        start_time = time.time()
        threshold = confidence_threshold or self._default_threshold

        # Get source entities
        source_entities: List[Entity] = []

        if document_id:
            entity_ids = self._document_entities.get(document_id, [])
            source_entities = [self._entities[eid] for eid in entity_ids if eid in self._entities]

        if query_text:
            # Find entities matching the query via semantic search
            query_entities = await self._search_entities_by_text(query_text, top_k=50)
            source_entities.extend(query_entities)

        if not source_entities:
            return LinkResult(
                document_id=document_id,
                query_id=query_text,
                links=[],
                total_entities_processed=0,
                total_links_found=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                packs_used=[],
                confidence_threshold=threshold,
            )

        # Filter by entity types if specified
        if entity_types:
            source_entities = [e for e in source_entities if e.type in entity_types]

        # Get all target entities (excluding sources to avoid self-links)
        source_ids = {e.id for e in source_entities}
        target_entities = [e for e in self._entities.values() if e.id not in source_ids]

        # Filter targets by entity types if specified
        if entity_types:
            target_entities = [e for e in target_entities if e.type in entity_types]

        # Get active packs
        active_packs = self._get_active_packs(packs)

        # Find links
        links = await self._find_links_between(
            source_entities,
            target_entities,
            active_packs,
            threshold,
        )

        # Filter by link types if specified
        if link_types:
            links = [link for link in links if link.link_type in link_types]

        # Sort by confidence and limit
        links.sort(key=lambda x: x.confidence, reverse=True)
        links = links[:max_links]

        processing_time = (time.time() - start_time) * 1000

        return LinkResult(
            document_id=document_id,
            query_id=query_text,
            links=links,
            total_entities_processed=len(source_entities),
            total_links_found=len(links),
            processing_time_ms=processing_time,
            packs_used=[p.name for p in active_packs],
            confidence_threshold=threshold,
        )

    def get_evidence(self, link_id: UUID) -> Optional[EvidenceResponse]:
        """
        Get detailed evidence for a specific link.

        Args:
            link_id: UUID of the link.

        Returns:
            EvidenceResponse with full evidence details and explanation.
        """
        link = self._links.get(link_id)
        if not link:
            return None

        # Build human-readable explanation
        explanation = self._build_explanation(link)

        return EvidenceResponse(
            link_id=link.id,
            source=link.source,
            target=link.target,
            link_type=link.link_type,
            confidence=link.confidence,
            evidence=link.evidence,
            explanation=explanation,
        )

    def get_links_for_document(self, document_id: str) -> List[Link]:
        """Get all links involving a document."""
        entity_ids = set(self._document_entities.get(document_id, []))
        if not entity_ids:
            return []

        return [
            link for link in self._links.values()
            if link.source.id in entity_ids or link.target.id in entity_ids
        ]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def get_link(self, link_id: UUID) -> Optional[Link]:
        """Get a link by ID."""
        return self._links.get(link_id)

    # -------------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------------

    def _get_active_packs(self, pack_names: Optional[List[str]]) -> List[BasePack]:
        """Get active packs, optionally filtered by names."""
        if pack_names:
            return [
                self._packs[name]
                for name in pack_names
                if name in self._packs and self._packs[name].config.enabled
            ]
        return [pack for pack in self._packs.values() if pack.config.enabled]

    async def _compute_embeddings(self, entities: List[Entity]) -> None:
        """Compute and cache embeddings for entities."""
        texts = [e.text for e in entities]

        if self._use_openai and _openai_client:
            embeddings = await self._compute_openai_embeddings(texts)
        elif self._embedding_model:
            embeddings = await self._compute_local_embeddings(texts)
        else:
            # No embedding capability
            return

        if embeddings is None:
            return

        # Cache embeddings
        for entity, embedding in zip(entities, embeddings):
            self._embeddings[entity.id] = embedding

            # Add to FAISS index
            if self._faiss_index is not None:
                try:
                    idx = self._faiss_index.ntotal
                    self._faiss_index.add(np.array([embedding], dtype="float32"))
                    self._faiss_id_map[idx] = entity.id
                except Exception as e:
                    logger.warning("Failed to add to FAISS: %s", e)

    async def _compute_local_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """Compute embeddings using local sentence transformer."""
        if not texts or self._embedding_model is None:
            return None

        try:
            embeddings = await asyncio.to_thread(
                self._embedding_model.encode,
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return embeddings
        except Exception as e:
            logger.warning("Local embedding failed: %s", e)
            return None

    async def _compute_openai_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """Compute embeddings using OpenAI API."""
        if not texts or _openai_client is None:
            return None

        try:
            # Batch texts (OpenAI has limits)
            batch_size = 100
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = _openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=batch,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            embeddings = np.array(all_embeddings, dtype="float32")

            # Normalize
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            embeddings = embeddings / norms

            return embeddings

        except Exception as e:
            logger.warning("OpenAI embedding failed: %s", e)
            return None

    async def _search_entities_by_text(
        self,
        query_text: str,
        top_k: int = 50,
    ) -> List[Entity]:
        """Search for entities similar to query text."""
        # Compute query embedding
        if self._use_openai:
            embeddings = await self._compute_openai_embeddings([query_text])
        else:
            embeddings = await self._compute_local_embeddings([query_text])

        if embeddings is None or len(embeddings) == 0:
            # Fall back to keyword search
            return self._keyword_search_entities(query_text, top_k)

        query_embedding = embeddings[0]

        # Search using FAISS if available
        if self._faiss_index is not None and self._faiss_index.ntotal > 0:
            try:
                distances, indices = self._faiss_index.search(
                    np.array([query_embedding], dtype="float32"),
                    min(top_k, self._faiss_index.ntotal),
                )

                results = []
                for idx, score in zip(indices[0], distances[0]):
                    if idx < 0:
                        continue
                    entity_id = self._faiss_id_map.get(int(idx))
                    if entity_id and entity_id in self._entities:
                        results.append(self._entities[entity_id])

                return results

            except Exception as e:
                logger.warning("FAISS search failed: %s", e)

        # Brute force similarity
        similarities = []
        for entity_id, embedding in self._embeddings.items():
            sim = float(np.dot(query_embedding, embedding))
            similarities.append((entity_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)

        return [
            self._entities[eid]
            for eid, _ in similarities[:top_k]
            if eid in self._entities
        ]

    def _keyword_search_entities(self, query: str, top_k: int) -> List[Entity]:
        """Fall back keyword search for entities."""
        query_words = set(query.lower().split())

        scored = []
        for entity in self._entities.values():
            entity_words = set(entity.text.lower().split())
            overlap = len(query_words & entity_words)
            if overlap > 0:
                scored.append((entity, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [e for e, _ in scored[:top_k]]

    async def _find_links_for_entities(
        self,
        entities: List[Entity],
        packs: List[BasePack],
    ) -> List[Link]:
        """Find links for newly extracted entities."""
        # Get all existing entities as targets
        target_entities = list(self._entities.values())

        return await self._find_links_between(
            entities,
            target_entities,
            packs,
            self._default_threshold,
        )

    async def _find_links_between(
        self,
        source_entities: List[Entity],
        target_entities: List[Entity],
        packs: List[BasePack],
        threshold: float,
    ) -> List[Link]:
        """Find links between source and target entities using packs."""
        all_links: List[Link] = []

        for pack in packs:
            try:
                # Filter entities to those handled by this pack
                source_filtered = [
                    e for e in source_entities
                    if e.type in pack.entity_types
                ]
                target_filtered = [
                    e for e in target_entities
                    if e.type in pack.entity_types
                ]

                if not source_filtered or not target_filtered:
                    continue

                # Get embeddings for matching
                embeddings = {
                    eid: emb
                    for eid, emb in self._embeddings.items()
                    if eid in {e.id for e in source_filtered + target_filtered}
                }

                # Match entities
                matches = pack.match_entities(
                    source_filtered,
                    target_filtered,
                    embeddings,
                )

                # Create links from matches
                for source, target, link_type, confidence, evidence in matches:
                    if confidence >= threshold:
                        link = pack.create_link(
                            source, target, link_type, confidence, evidence
                        )
                        all_links.append(link)

            except Exception as e:
                logger.exception("Pack %s failed during matching: %s", pack.name, e)

        return all_links

    def _build_explanation(self, link: Link) -> str:
        """Build a human-readable explanation for a link."""
        parts = []

        # Describe the relationship
        parts.append(
            f"This link connects '{link.source.type.value}' ({link.source.id}) "
            f"to '{link.target.type.value}' ({link.target.id}) "
            f"via a '{link.link_type.value}' relationship."
        )

        # Describe confidence
        if link.confidence >= 0.9:
            conf_desc = "very high"
        elif link.confidence >= 0.8:
            conf_desc = "high"
        elif link.confidence >= 0.7:
            conf_desc = "moderate"
        else:
            conf_desc = "low"

        parts.append(f"The confidence level is {conf_desc} ({link.confidence:.0%}).")

        # Describe evidence
        if link.evidence:
            parts.append("Evidence supporting this link:")
            for ev in link.evidence:
                if ev.type == EvidenceType.SEMANTIC_SIMILARITY:
                    parts.append(f"  - Semantic similarity: {float(ev.value):.0%}")
                elif ev.type == EvidenceType.KEYWORD_MATCH:
                    keywords = ev.metadata.get("matched_keywords", [])
                    parts.append(f"  - Keyword match: {', '.join(keywords[:5])}")
                elif ev.type == EvidenceType.CSI_CODE_MATCH:
                    codes = ev.metadata.get("matched_codes", [])
                    parts.append(f"  - CSI code match: {', '.join(codes)}")
                elif ev.type == EvidenceType.MATERIAL_MATCH:
                    materials = ev.metadata.get("matched_materials", [])
                    parts.append(f"  - Material match: {', '.join(materials)}")
                elif ev.type == EvidenceType.COST_CODE_MATCH:
                    codes = ev.metadata.get("matched_codes", [])
                    parts.append(f"  - Cost code match: {', '.join(codes)}")
                elif ev.type == EvidenceType.QUANTITY_REFERENCE:
                    parts.append(
                        f"  - Amount match: {ev.source_text} ~ {ev.target_text}"
                    )
                elif ev.type == EvidenceType.DRAWING_REFERENCE:
                    drawings = ev.metadata.get("matched_drawings", [])
                    parts.append(f"  - Drawing reference: {', '.join(drawings)}")
                elif ev.type == EvidenceType.CLAUSE_REFERENCE:
                    refs = ev.metadata.get("matched_references", [])
                    parts.append(f"  - Reference match: {', '.join(refs)}")
                elif ev.type == EvidenceType.DATE_PROXIMITY:
                    days = ev.metadata.get("day_difference", 0)
                    parts.append(f"  - Date proximity: {days} days apart")

        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # Persistence helpers (for database integration)
    # -------------------------------------------------------------------------

    def export_links(self) -> List[Dict[str, Any]]:
        """Export all links as dictionaries for database storage."""
        return [
            {
                "id": str(link.id),
                "source_entity_id": link.source.id,
                "source_entity_type": link.source.type.value,
                "target_entity_id": link.target.id,
                "target_entity_type": link.target.type.value,
                "link_type": link.link_type.value,
                "confidence": link.confidence,
                "evidence": [e.model_dump() for e in link.evidence],
                "pack_name": link.pack_name,
                "created_at": link.created_at.isoformat(),
                "validated": link.validated,
                "metadata": link.metadata,
            }
            for link in self._links.values()
        ]

    def import_link(self, data: Dict[str, Any]) -> None:
        """Import a link from database storage."""
        from uuid import UUID as UUIDType
        from datetime import datetime

        # Reconstruct entities (minimal)
        source = Entity(
            id=data["source_entity_id"],
            type=EntityType(data["source_entity_type"]),
            text=data.get("source_text", ""),
        )
        target = Entity(
            id=data["target_entity_id"],
            type=EntityType(data["target_entity_type"]),
            text=data.get("target_text", ""),
        )

        # Reconstruct evidence
        evidence = [Evidence(**e) for e in data.get("evidence", [])]

        link = Link(
            id=UUIDType(data["id"]),
            source=source,
            target=target,
            link_type=LinkType(data["link_type"]),
            confidence=data["confidence"],
            evidence=evidence,
            pack_name=data["pack_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            validated=data.get("validated", False),
            metadata=data.get("metadata", {}),
        )

        self._links[link.id] = link

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        link_types_count: Dict[str, int] = {}
        entity_types_count: Dict[str, int] = {}

        for link in self._links.values():
            lt = link.link_type.value
            link_types_count[lt] = link_types_count.get(lt, 0) + 1

        for entity in self._entities.values():
            et = entity.type.value
            entity_types_count[et] = entity_types_count.get(et, 0) + 1

        return {
            "total_packs": len(self._packs),
            "total_entities": len(self._entities),
            "total_links": len(self._links),
            "total_documents": len(self._document_entities),
            "total_embeddings": len(self._embeddings),
            "entity_types": entity_types_count,
            "link_types": link_types_count,
            "packs": [p.name for p in self._packs.values()],
            "embeddings_enabled": self._embedding_model is not None or self._use_openai,
            "faiss_enabled": self._faiss_index is not None,
        }


