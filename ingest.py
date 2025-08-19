import os, glob, re, uuid, pathlib
from typing import List, Tuple
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
from PyPDF2 import PdfReader

load_dotenv()

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
DB_PATH = os.getenv("DB_PATH", "./ragdb")

embedder = SentenceTransformer(EMBED_MODEL_NAME)
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="hrlaw")

DATA_DIR = os.getenv("DATA_DIR", "./sample_data")

def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def read_md(path: str) -> str:
    return read_txt(path)

def read_pdf(path: str) -> str:
    text = []
    reader = PdfReader(path)
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    # Simple word-based chunking
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
        if i < 0: break
    return chunks

def ingest_file(path: str, title: str):
    ext = pathlib.Path(path).suffix.lower()
    if ext == ".pdf":
        raw = read_pdf(path)
    elif ext in (".txt", ".md"):
        raw = read_txt(path)
    else:
        print(f"Skipping unsupported file: {path}")
        return

    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        print(f"Empty file: {path}")
        return

    chunks = chunk_text(raw, chunk_size=1200, overlap=200)
    print(f"Ingesting {path} -> {len(chunks)} chunks")
    for idx, ch in enumerate(chunks):
        emb = embedder.encode([ch])[0].tolist()
        collection.add(
            documents=[ch],
            metadatas=[{"title": title}],
            ids=[f"{title}_{uuid.uuid4().hex}_{idx}"]
        )

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    paths = []
    paths += glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    paths += glob.glob(os.path.join(DATA_DIR, "*.txt"))
    paths += glob.glob(os.path.join(DATA_DIR, "*.md"))

    if not paths:
        print("No files found in DATA_DIR. Add PDFs/TXT/MD to './sample_data' and re-run.")
        return

    for p in paths:
        title = pathlib.Path(p).stem
        ingest_file(p, title)

if __name__ == "__main__":
    main()
