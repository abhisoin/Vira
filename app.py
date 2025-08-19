import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import requests

# Embeddings / Vector DB
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", "8000"))

# Initialize FastAPI
app = FastAPI(title="HR Law Bot RAG API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize embeddings + ChromaDB
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
embedder = SentenceTransformer(EMBED_MODEL_NAME)

# Persistent client in ./ragdb
DB_PATH = os.getenv("DB_PATH", "./ragdb")
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="hrlaw")

class AskPayload(BaseModel):
    question: str
    session_id: Optional[str] = None
    top_k: Optional[int] = 5

SYSTEM_PROMPT = """You are HR Law Bot, a cautious, India-focused assistant for HR & labour compliance.
Use only the provided context to answer. If the context is insufficient or state-specific details are missing, say so and recommend checking the relevant state Shops & Establishments Act or consulting a professional.
Format:
- One-paragraph answer.
- Key Points: 3–5 concise bullets.
- Sources: list the provided source titles only.
Never fabricate citations, sections, or dates. Be clear when something varies by state or requires verification.
"""

def openai_chat(system_prompt: str, user_msg: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI error {r.status_code}: {r.text}")
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/hrlaw/rag")
def rag_answer(payload: AskPayload):
    q = (payload.question or "").strip()
    if not q:
        raise HTTPException(400, "Missing 'question'")

    top_k = payload.top_k or 5

    # Query vector DB
    q_emb = embedder.encode([q])[0].tolist()
    results = collection.query(query_embeddings=[q_emb], n_results=top_k)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    # Build context + gather sources
    context = ""
    seen_titles = []
    for doc, meta in zip(docs, metas):
        title = meta.get("title", "Source")
        context += f"\n[Source: {title}]\n{doc}\n"
        if title not in seen_titles:
            seen_titles.append(title)

    # If no context, say so (still let LLM answer with caution)
    user_msg = f"Question: {q}\n\nContext:\n{context}\n\nAnswer:"
    try:
        answer = openai_chat(SYSTEM_PROMPT, user_msg)
    except Exception as e:
        raise HTTPException(500, f"LLM error: {e}")

    sources = ", ".join(seen_titles) if seen_titles else "Context not sufficient; please consult official sources."
    return {"answer": answer, "sources": sources}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
