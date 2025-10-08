"""Semantic search engine utilities with Render-friendly fallbacks."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore[assignment]

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    faiss = None  # type: ignore[assignment]

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None  # type: ignore[assignment]
    Settings = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Supported document types."""

    CAD_DRAWING = "cad_drawing"
    BIM_MODEL = "bim_model"
    BOQ = "boq"
    SCHEDULE = "schedule"
    SPECIFICATION = "specification"
    CONTRACT = "contract"
    REPORT = "report"
    EMAIL = "email"
    PHOTO = "photo"
    VIDEO = "video"
    RFI = "rfi"
    SUBMITTAL = "submittal"


class SearchMode(str, Enum):
    """Search strategy options."""

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    NEURAL = "neural"


@dataclass(slots=True)
class SearchResult:
    """Representation of an individual search hit."""

    document_id: str
    title: str
    content: str
    doc_type: DocumentType
    relevance_score: float
    metadata: Dict[str, Any]
    snippet: str
    highlights: List[str]
    source_path: str
    created_date: datetime
    modified_date: datetime


@dataclass(slots=True)
class SearchQuery:
    """Search parameters supplied by the caller."""

    query_text: str
    doc_types: Optional[List[DocumentType]] = None
    search_mode: SearchMode = SearchMode.HYBRID
    max_results: int = 20
    min_score: float = 0.5
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    project_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    use_reranking: bool = True
    expanded_text: Optional[str] = None


class EnhancedSemanticSearch:
    """Hybrid semantic search helper resilient to optional dependency gaps."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chroma_path: str = "./chroma_db",
        openai_api_key: Optional[str] = None,
    ) -> None:
        self._model_name = model_name
        self._embedding_model: Optional[SentenceTransformer] = None
        self._embedding_dimension: Optional[int] = None
        self._faiss_index = None
        self._faiss_ids: Dict[int, str] = {}
        self._chroma_client = None
        self._collections: Dict[DocumentType, Any] = {}
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._query_cache: Dict[str, List[SearchResult]] = {}
        self.search_history: List[Dict[str, Any]] = []

        self._initialise_embedding_model()
        self._initialise_vector_index()
        self._initialise_chroma(chroma_path)

        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self._openai_client = None
        if api_key and OpenAI is not None:
            try:
                self._openai_client = OpenAI(api_key=api_key)
            except Exception:  # pragma: no cover - defensive safeguard
                logger.exception("Failed to initialise OpenAI client for semantic search.")
                self._openai_client = None

        logger.info(
            "Semantic search ready: embeddings=%s, chroma=%s, faiss=%s",
            self._embedding_model is not None,
            self._chroma_client is not None,
            self._faiss_index is not None,
        )

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _initialise_embedding_model(self) -> None:
        if SentenceTransformer is None:
            logger.warning("sentence-transformers not installed; semantic ranking disabled.")
            return
        try:
            self._embedding_model = SentenceTransformer(self._model_name)
            self._embedding_dimension = self._embedding_model.get_sentence_embedding_dimension()
        except Exception:  # pragma: no cover - model load failures
            logger.exception("Failed to load sentence transformer model; falling back to keyword search.")
            self._embedding_model = None
            self._embedding_dimension = None

    def _initialise_vector_index(self) -> None:
        if self._embedding_dimension is None or faiss is None:
            if faiss is None:
                logger.warning("faiss-cpu is unavailable; using in-memory similarity checks.")
            return
        try:
            self._faiss_index = faiss.IndexFlatIP(self._embedding_dimension)
        except Exception:  # pragma: no cover - faiss failures
            logger.exception("Failed to create FAISS index; disabling vector acceleration.")
            self._faiss_index = None

    def _initialise_chroma(self, chroma_path: str) -> None:
        if chromadb is None or Settings is None:
            logger.warning("ChromaDB not installed; semantic index persistence disabled.")
            return
        try:
            self._chroma_client = chromadb.Client(
                Settings(chroma_db_impl="duckdb+parquet", persist_directory=chroma_path)
            )
        except Exception:  # pragma: no cover - chroma failures
            logger.exception("Failed to connect to ChromaDB; operating without persistent vectors.")
            self._chroma_client = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def semantic_ready(self) -> bool:
        """Return ``True`` when semantic components are fully available."""

        return self._embedding_model is not None and self._chroma_client is not None

    async def index_document(
        self,
        doc_id: str,
        content: str,
        title: str,
        doc_type: DocumentType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Index a single document for later retrieval."""

        if not doc_id or not content:
            logger.warning("Skipping indexing for empty document payload (%s).", doc_id)
            return False

        metadata = metadata or {}
        now = datetime.now()
        stored_metadata = {
            **metadata,
            "doc_type": doc_type.value,
            "title": title,
            "indexed_at": now.isoformat(),
        }
        self._documents[doc_id] = {
            "title": title,
            "content": content,
            "doc_type": doc_type,
            "metadata": stored_metadata,
        }

        if not self.semantic_ready:
            return True

        try:
            embedding = await asyncio.to_thread(
                self._embedding_model.encode,  # type: ignore[union-attr]
                content,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            norm = np.linalg.norm(embedding)
            if norm == 0:
                logger.warning("Zero embedding norm for document %s; storing keyword-only.", doc_id)
                return True
            embedding = embedding / norm
        except Exception:  # pragma: no cover - encoding failures
            logger.exception("Failed to embed document %s; continuing with keyword fallback.", doc_id)
            return True

        if self._chroma_client is not None:
            collection = self._collections.get(doc_type)
            if collection is None:
                try:
                    collection = self._chroma_client.get_or_create_collection(
                        name=f"diriyah_{doc_type.value}", metadata={"hnsw:space": "cosine"}
                    )
                    self._collections[doc_type] = collection
                except Exception:  # pragma: no cover - collection failures
                    logger.exception("Failed to create Chroma collection for %s.", doc_type.value)
                    collection = None
            if collection is not None:
                try:
                    collection.add(
                        documents=[content],
                        embeddings=[embedding.tolist()],
                        metadatas=[stored_metadata],
                        ids=[doc_id],
                    )
                except Exception:  # pragma: no cover - chroma add failures
                    logger.exception("Chroma indexing failed for %s; continuing without persistence.", doc_id)

        if self._faiss_index is not None:
            try:
                row = np.array([embedding], dtype="float32")
                index_id = self._faiss_index.ntotal
                self._faiss_index.add(row)
                self._faiss_ids[index_id] = doc_id
            except Exception:  # pragma: no cover - faiss failures
                logger.exception("Failed to register FAISS vector for %s.", doc_id)

        return True

    async def index_documents_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Index multiple documents sequentially."""

        summary = {"success": 0, "failed": 0}
        for doc in documents:
            try:
                success = await self.index_document(
                    doc_id=doc["doc_id"],
                    content=doc["content"],
                    title=doc.get("title", "Untitled"),
                    doc_type=DocumentType(doc["doc_type"]),
                    metadata=doc.get("metadata"),
                )
                summary["success" if success else "failed"] += 1
            except Exception:  # pragma: no cover - defensive catch
                logger.exception("Failed to index document batch item: %s", doc)
                summary["failed"] += 1
        return summary

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute a search query returning ranked results."""

        cache_key = self._build_cache_key(query)
        cached = self._query_cache.get(cache_key)
        if cached is not None:
            return cached

        expanded_query = query.expanded_text or await self._expand_query(query.query_text)
        if query.search_mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(expanded_query, query)
        elif query.search_mode == SearchMode.KEYWORD:
            results = await self._keyword_search(query.query_text, query)
        elif query.search_mode == SearchMode.NEURAL:
            results = await self._neural_search(expanded_query, query)
        else:
            results = await self._hybrid_search(expanded_query, query)

        if query.use_reranking and results:
            results = await self._rerank_results(query.query_text, results)

        filtered = [r for r in results if r.relevance_score >= query.min_score]
        limited = filtered[: query.max_results]

        self._query_cache[cache_key] = limited
        self._log_search(query, len(limited))
        return limited

    def get_search_analytics(self) -> Dict[str, Any]:
        """Return lightweight analytics for recent searches."""

        if not self.search_history:
            return {"total_searches": 0, "recent_queries": [], "popular_doc_types": []}

        return {
            "total_searches": len(self.search_history),
            "recent_queries": [s["query"] for s in self.search_history[-10:]],
            "popular_doc_types": self._popular_doc_types(),
            "avg_results_per_search": float(
                np.mean([s["num_results"] for s in self.search_history])
            ),
        }

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------
    async def _semantic_search(self, query_text: str, query: SearchQuery) -> List[SearchResult]:
        if not self.semantic_ready:
            return await self._keyword_search(query.query_text, query)

        try:
            embedding = await asyncio.to_thread(
                self._embedding_model.encode,  # type: ignore[union-attr]
                query_text,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            norm = np.linalg.norm(embedding)
            if norm == 0:
                return []
            embedding = embedding / norm
        except Exception:  # pragma: no cover - encoding failures
            logger.exception("Failed to encode query; falling back to keyword search.")
            return await self._keyword_search(query.query_text, query)

        doc_types = query.doc_types or list(DocumentType)
        results: List[SearchResult] = []
        for doc_type in doc_types:
            collection = self._collections.get(doc_type)
            if collection is None:
                try:
                    collection = self._chroma_client.get_collection(f"diriyah_{doc_type.value}")
                    self._collections[doc_type] = collection
                except Exception:
                    continue
            try:
                response = collection.query(
                    query_embeddings=[embedding.tolist()],
                    n_results=query.max_results,
                    where=self._build_where_clause(query),
                )
            except Exception:  # pragma: no cover - query failure
                logger.exception("Chroma query failed for %s.", doc_type.value)
                continue

            ids_raw = response.get("ids") or [[]]
            documents_raw = response.get("documents") or [[]]
            metadatas_raw = response.get("metadatas") or [[]]
            distances_raw = response.get("distances") or [[]]

            ids = ids_raw[0] if ids_raw else []
            documents = documents_raw[0] if documents_raw else []
            metadatas = metadatas_raw[0] if metadatas_raw else []
            distances = distances_raw[0] if distances_raw else []
            for idx, doc_id in enumerate(ids):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                content = documents[idx] if idx < len(documents) else ""
                distance = distances[idx] if idx < len(distances) else 0.0
                score = max(0.0, min(1.0, 1 - (distance / 2)))
                results.append(self._build_result(doc_id, content, metadata, score, query.query_text))

        results.sort(key=lambda item: item.relevance_score, reverse=True)
        return results

    async def _keyword_search(self, query_text: str, query: SearchQuery) -> List[SearchResult]:
        keywords = [term for term in query_text.lower().split() if term]
        if not keywords:
            return []

        results: List[SearchResult] = []
        for doc_id, data in self._documents.items():
            if query.doc_types and data["doc_type"] not in query.doc_types:
                continue
            content_lower = data["content"].lower()
            title_lower = data["title"].lower()
            matches = sum(1 for kw in keywords if kw in content_lower or kw in title_lower)
            if matches == 0:
                continue
            score = matches / len(keywords)
            results.append(
                self._build_result(
                    doc_id,
                    data["content"],
                    data["metadata"],
                    min(1.0, score),
                    query_text,
                )
            )

        results.sort(key=lambda item: item.relevance_score, reverse=True)
        return results

    async def _hybrid_search(self, query_text: str, query: SearchQuery) -> List[SearchResult]:
        semantic_results = await self._semantic_search(query_text, query)
        keyword_results = await self._keyword_search(query.query_text, query)

        combined: Dict[str, SearchResult] = {}
        for result in semantic_results:
            combined[result.document_id] = result
            result.relevance_score *= 0.7
        for result in keyword_results:
            existing = combined.get(result.document_id)
            if existing is None:
                result.relevance_score *= 0.3
                combined[result.document_id] = result
            else:
                existing.relevance_score = min(1.0, existing.relevance_score + result.relevance_score * 0.3)
        return sorted(combined.values(), key=lambda item: item.relevance_score, reverse=True)

    async def _neural_search(self, query_text: str, query: SearchQuery) -> List[SearchResult]:
        base_results = await self._semantic_search(query_text, query)
        if not self._openai_client:
            return base_results
        return await self._rerank_results(query.query_text, base_results)

    async def _rerank_results(self, query_text: str, results: List[SearchResult]) -> List[SearchResult]:
        if not self._openai_client or not results:
            return results

        prompt_docs = []
        for index, result in enumerate(results[:10], start=1):
            prompt_docs.append(
                f"Document {index}:\nTitle: {result.title}\nSnippet: {result.snippet}"
            )
        prompt = (
            "Given the search query: \"{query}\"\n\n".format(query=query_text)
            + "Rank the following documents by relevance (1 is best).\n\n"
            + "\n\n".join(prompt_docs)
            + "\n\nReturn a JSON array of document numbers in ranked order."
        )

        try:
            response = self._openai_client.chat.completions.create(  # type: ignore[union-attr]
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You help rank documents by relevance."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=200,
            )
            payload = response.choices[0].message.content.strip()
            ranking = json.loads(payload)
        except Exception:  # pragma: no cover - API failures
            logger.exception("OpenAI re-ranking failed; returning original ordering.")
            return results

        ordered: List[SearchResult] = []
        for item in ranking:
            try:
                idx = int(item) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(results):
                candidate = results[idx]
                candidate.relevance_score = max(0.0, 1.0 - (len(ordered) * 0.05))
                ordered.append(candidate)
        for result in results:
            if result not in ordered:
                ordered.append(result)
        return ordered

    async def _expand_query(self, query_text: str) -> str:
        if not self._openai_client:
            return query_text

        try:
            response = self._openai_client.chat.completions.create(  # type: ignore[union-attr]
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Expand the search query with concise synonyms and related terms.",
                    },
                    {"role": "user", "content": query_text},
                ],
                temperature=0.3,
                max_tokens=80,
            )
            expanded = response.choices[0].message.content.strip()
            if expanded:
                logger.debug("Expanded query '%s' -> '%s'", query_text, expanded)
                return expanded
        except Exception:  # pragma: no cover - API failures
            logger.exception("Query expansion failed; using original query.")
        return query_text

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _build_cache_key(self, query: SearchQuery) -> str:
        doc_type_key = ",".join(dt.value for dt in query.doc_types or [])
        return "|".join(
            [
                query.query_text,
                query.search_mode.value,
                str(query.max_results),
                doc_type_key,
                query.expanded_text or "",
                json.dumps(query.filters or {}, sort_keys=True),
            ]
        )

    def _log_search(self, query: SearchQuery, num_results: int) -> None:
        self.search_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "query": query.query_text,
                "mode": query.search_mode.value,
                "num_results": num_results,
                "doc_types": [dt.value for dt in query.doc_types or []],
            }
        )

    def _popular_doc_types(self) -> List[str]:
        counts: Dict[str, int] = {}
        for record in self.search_history:
            for value in record.get("doc_types", []):
                counts[value] = counts.get(value, 0) + 1
        return [item[0] for item in sorted(counts.items(), key=lambda row: row[1], reverse=True)[:5]]

    def _build_where_clause(self, query: SearchQuery) -> Optional[Dict[str, Any]]:
        filters: Dict[str, Any] = {}
        if query.project_id:
            filters["project_id"] = query.project_id
        if query.filters:
            filters.update(query.filters)
        return filters or None

    def _build_result(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any],
        score: float,
        query_text: str,
    ) -> SearchResult:
        safe_metadata = dict(metadata or {})
        safe_metadata["last_query"] = query_text

        created = self._parse_datetime(safe_metadata.get("created_date"))
        modified = self._parse_datetime(safe_metadata.get("modified_date"))
        title = safe_metadata.get("title", self._documents.get(doc_id, {}).get("title", "Untitled"))
        doc_type_value = safe_metadata.get("doc_type")
        doc_type = self._documents.get(doc_id, {}).get("doc_type", DocumentType.REPORT)
        if doc_type_value:
            try:
                doc_type = DocumentType(doc_type_value)
            except ValueError:
                logger.warning("Unknown document type '%s' for %s; defaulting to %s.", doc_type_value, doc_id, doc_type)

        snippet = self._create_snippet(content, query_text)
        highlights = self._extract_highlights(content, query_text)
        source_path = safe_metadata.get("source_path", "")
        result = SearchResult(
            document_id=doc_id,
            title=title,
            content=content,
            doc_type=doc_type,
            relevance_score=float(score),
            metadata=safe_metadata,
            snippet=snippet,
            highlights=highlights,
            source_path=source_path,
            created_date=created,
            modified_date=modified,
        )
        return result

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now()
        try:
            return datetime.fromisoformat(value)
        except Exception:  # pragma: no cover - invalid format
            return datetime.now()

    def _create_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        if not content:
            return ""
        content_length = len(content)
        if content_length <= max_length:
            return content

        query_terms = [term for term in query.lower().split() if term]
        if not query_terms:
            start = max(0, content_length // 2 - max_length // 2)
            end = min(content_length, start + max_length)
            snippet = content[start:end]
        else:
            content_lower = content.lower()
            best_start = 0
            best_matches = -1
            for idx in range(0, max(1, content_length - max_length), 50):
                segment = content_lower[idx : idx + max_length]
                matches = sum(1 for term in query_terms if term in segment)
                if matches > best_matches:
                    best_matches = matches
                    best_start = idx
            snippet = content[best_start : best_start + max_length]

        prefix = "..." if not content.startswith(snippet) else ""
        suffix = "..." if not content.endswith(snippet) else ""
        return f"{prefix}{snippet}{suffix}"

    def _extract_highlights(self, content: str, query: str, limit: int = 3) -> List[str]:
        if not content or not query:
            return []
        query_terms = [term for term in query.lower().split() if term]
        if not query_terms:
            return []
        sentences = [sentence.strip() for sentence in content.split('.') if sentence.strip()]
        highlights: List[str] = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(term in lowered for term in query_terms):
                highlights.append(sentence)
            if len(highlights) >= limit:
                break
        return highlights


class SearchAPI:
    """FastAPI integration helper for semantic search."""

    def __init__(self, engine: EnhancedSemanticSearch) -> None:
        self._engine = engine

    async def search_endpoint(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        mode: str = SearchMode.HYBRID.value,
        max_results: int = 20,
        use_reranking: bool = True,
    ) -> Dict[str, Any]:
        try:
            search_mode = SearchMode(mode)
        except ValueError:
            search_mode = SearchMode.HYBRID

        resolved_doc_types: Optional[List[DocumentType]] = None
        if doc_types:
            resolved_doc_types = []
            for value in doc_types:
                try:
                    resolved_doc_types.append(DocumentType(value))
                except ValueError:
                    logger.warning("Ignoring unsupported document type: %s", value)

        expanded_query = await self._engine._expand_query(query)

        query_model = SearchQuery(
            query_text=query,
            doc_types=resolved_doc_types,
            search_mode=search_mode,
            max_results=max_results,
            use_reranking=use_reranking,
            expanded_text=expanded_query,
        )

        results = await self._engine.search(query_model)
        return {
            "query": query,
            "mode": search_mode.value,
            "expanded_query": expanded_query,
            "total_results": len(results),
            "results": [
                {
                    "id": item.document_id,
                    "title": item.title,
                    "snippet": item.snippet,
                    "score": item.relevance_score,
                    "type": item.doc_type.value,
                    "highlights": item.highlights,
                    "metadata": item.metadata,
                }
                for item in results
            ],
            "search_metadata": {
                "reranking_used": use_reranking and self._engine._openai_client is not None,
                "timestamp": datetime.now().isoformat(),
            },
        }


async def example_usage() -> None:  # pragma: no cover - illustrative helper
    engine = EnhancedSemanticSearch()
    await engine.index_documents_batch(
        [
            {
                "doc_id": "CAD-001",
                "title": "Site Plan Drawing",
                "content": "Main entrance plaza with fountain and landscaping. Includes parking area for 500 vehicles.",
                "doc_type": "cad_drawing",
                "metadata": {"project_id": "PROJ-001", "created_date": datetime.now().isoformat()},
            },
            {
                "doc_id": "BOQ-001",
                "title": "Bill of Quantities - Foundation",
                "content": "Concrete foundation works: 5000 cubic meters of C30 concrete, 200 tons of reinforcement steel.",
                "doc_type": "boq",
                "metadata": {"project_id": "PROJ-001", "created_date": datetime.now().isoformat()},
            },
        ]
    )

    query = SearchQuery(query_text="parking and entrance", search_mode=SearchMode.SEMANTIC, max_results=5)
    results = await engine.search(query)
    for result in results:
        logger.info("Found document %s (%s) score=%.2f", result.document_id, result.title, result.relevance_score)


if __name__ == "__main__":  # pragma: no cover - manual debugging hook
    asyncio.run(example_usage())


__all__ = [
    "DocumentType",
    "SearchMode",
    "SearchResult",
    "SearchQuery",
    "EnhancedSemanticSearch",
    "SearchAPI",
]
