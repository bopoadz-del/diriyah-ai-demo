import importlib.util
import os
import pickle

import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI

_TRANSFORMERS_AVAILABLE = importlib.util.find_spec("transformers") is not None
if _TRANSFORMERS_AVAILABLE:
    from transformers import pipeline

INDEX_PATH = "storage/faiss.index"
META_PATH = "storage/meta.pkl"
os.makedirs("storage", exist_ok=True)

embedder = SentenceTransformer("all-MiniLM-L6-v2")
_openai_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=_openai_key) if _openai_key else None
_fallback_generator = None
if _TRANSFORMERS_AVAILABLE:
    _fallback_generator = pipeline(
        "text-generation",
        model=os.getenv("HF_FALLBACK_MODEL", "gpt2"),
    )

if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)
else:
    index = faiss.IndexFlatL2(384)
    metadata = []

def _get_embedder():
    global _embedder
    if _embedder is None:
        sentence_transformers = importlib.import_module("sentence_transformers")
        model = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
        _embedder = model
    return _embedder


def _get_fallback_generator():
    global _fallback_generator
    if _fallback_generator is not None:
        return _fallback_generator
    if importlib.util.find_spec("transformers") is None:
        return None
    transformers = importlib.import_module("transformers")
    pipeline = getattr(transformers, "pipeline", None)
    if pipeline is None:
        return None
    _fallback_generator = pipeline(
        "text-generation",
        model=os.getenv("HF_FALLBACK_MODEL", "gpt2"),
    )
    return _fallback_generator


def _get_openai_client():
    global _openai_client, _openai_available
    if _openai_client is not None or not _openai_available:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _openai_available = False
        return None
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI", None)
        if OpenAI is None:
            _openai_available = False
            return None
        _openai_client = OpenAI(api_key=api_key)
    except Exception:
        _openai_available = False
        return None
    return _openai_client


def add_document(project_id: str, text: str, source: str):
    embedder = _get_embedder()
    vector = embedder.encode([text])
    index.add(vector)
    metadata.append({"project": project_id, "text": text, "source": source})
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)


def query_rag(project_id: str, query: str, top_k: int = 3):
    if len(metadata) == 0:
        return "No documents indexed yet."
    embedder = _get_embedder()
    qvec = embedder.encode([query])
    D, I = index.search(qvec, top_k)
    hits = [metadata[i] for i in I[0] if i < len(metadata) and metadata[i]["project"] == project_id]
    context = "\n\n".join([f"Source: {h['source']}\n{h['text']}" for h in hits])
    prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer concisely:"
    if client:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a construction project assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return resp.choices[0].message.content
        except Exception:
            pass

    if _fallback_generator:
        generated = _fallback_generator(prompt, max_new_tokens=200)
        if generated:
            return generated[0].get("generated_text", "No response available.")
    return "No response available."
