import faiss, os, pickle
from sentence_transformers import SentenceTransformer
from openai import OpenAI

INDEX_PATH = "storage/faiss.index"
META_PATH = "storage/meta.pkl"
os.makedirs("storage", exist_ok=True)

embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)
else:
    index = faiss.IndexFlatL2(384)
    metadata = []

def add_document(project_id: str, text: str, source: str):
    vector = embedder.encode([text])
    index.add(vector)
    metadata.append({"project": project_id, "text": text, "source": source})
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)

def query_rag(project_id: str, query: str, top_k: int = 3):
    if len(metadata) == 0:
        return "No documents indexed yet."
    qvec = embedder.encode([query])
    D, I = index.search(qvec, top_k)
    hits = [metadata[i] for i in I[0] if i < len(metadata) and metadata[i]["project"] == project_id]
    context = "\n\n".join([f"Source: {h['source']}\n{h['text']}" for h in hits])
    prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer concisely:"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a construction project assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return resp.choices[0].message.content