import os
from typing import List, Dict
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except Exception:
    chromadb = None
    SentenceTransformer = None

class MemoryStore:
    def __init__(self):
        self._fallback_docs: list[tuple[str, dict]] = []
        self.embedder = None
        self.client = None
        self.collection = None

        if chromadb and SentenceTransformer:
            try:
                if os.getenv("CHROMA_HOST"):
                    self.client = chromadb.HttpClient(
                        host=os.getenv("CHROMA_HOST", "chroma"),
                        port=int(os.getenv("CHROMA_PORT", "8000"))
                    )
                else:
                    self.client = chromadb.PersistentClient(path="chroma_db")
                self.collection = self.client.get_or_create_collection("chat_memory")
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.client = None
                self.collection = None
                self.embedder = None

    def add_message(self, text: str, metadata: Dict):
        if self.collection and self.embedder:
            emb = self.embedder.encode([text]).tolist()[0]
            self.collection.add(embeddings=[emb], documents=[text], metadatas=[metadata], ids=[f"msg_{metadata.get('id','0')}"])
        else:
            self._fallback_docs.append((text, metadata))

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        if self.collection and self.embedder:
            q = self.embedder.encode([query]).tolist()[0]
            res = self.collection.query(query_embeddings=[q], n_results=top_k)
            out = []
            for d, m, s in zip(res.get("documents", [[]])[0], res.get("metadatas", [[]])[0], res.get("distances", [[]])[0]):
                out.append({"text": d, "metadata": m, "score": s})
            return out
        # naive fallback: substring match
        out = []
        for t, m in self._fallback_docs[-50:]:
            if any(w in t.lower() for w in query.lower().split()):
                out.append({"text": t, "metadata": m, "score": 0.5})
        return out[:top_k]

memory_store = MemoryStore()
