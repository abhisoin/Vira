# HR Law Bot – RAG Backend (FastAPI + ChromaDB)

This is a **ready-to-run Retrieval-Augmented Generation backend** for the HR Law Bot.
- **Embeddings**: local Sentence-Transformers (`all-MiniLM-L6-v2`)
- **Vector DB**: ChromaDB (persistent)
- **LLM**: OpenAI Chat Completions (set `OPENAI_API_KEY`)

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

## 2) Add Documents

Place your **PDF/TXT/MD** files into `./sample_data`. Examples:
- Central Acts overviews (Maternity Benefit Act, POSH, Payment of Gratuity, EPF/ESI)
- State Shops & Establishments Act summaries
- Your curated HR Q&A

## 3) Ingest

```bash
python ingest.py
```

This chunks and indexes all files from `DATA_DIR` (default `./sample_data`) into ChromaDB at `DB_PATH`.

## 4) Run Server

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
# or: python app.py
```

Health check:
```
GET http://localhost:8000/health
```

Ask endpoint:
```
POST http://localhost:8000/hrlaw/rag
Content-Type: application/json

{
  "question": "Is maternity leave 26 weeks for all companies?",
  "top_k": 5
}
```

## 5) Wire into Typebot

- Add an **Input** block → save as `user_query`
- Add an **HTTP Request** block:
  - Method: `POST`
  - URL: `https://<your-domain-or-ip>:8000/hrlaw/rag`
  - Headers: `Content-Type: application/json`
  - Body:
    ```json
    {
      "question": "{{user_query}}",
      "session_id": "{{session.id}}"
    }
    ```
  - Map response to variables:
    - `ai_answer`  ← `response.answer`
    - `ai_sources` ← `response.sources`
- Show a **Message** block:
  ```markdown
  ✅ Here's the legal view:

  {{ai_answer}}

  **Sources**: {{ai_sources}}
  ```

Keep your **free-query limit** logic in Typebot (≥3 → Upgrade).

## Notes

- Outputs purposely include a **Sources** section with only the titles from your indexed corpus to avoid hallucinated citations.
- If you need stricter compliance, store and return document IDs and page ranges in `ingest.py` and include them in the answer.
- You can swap the OpenAI model via `.env` (`OPENAI_MODEL=`).

## Deploy

- Works on Render, Railway, Fly.io, or any VM.
- Ensure persistent storage for `./ragdb`.
- Expose port `8000`.
- Set `OPENAI_API_KEY` as an environment variable on your platform.
```

# End


---

## One‑Click Deploy to Render

1. Create a new **Private GitHub repo** and upload these files.
2. Add a new **Web Service** on [Render](https://render.com/), choose **"Build from a repo"**.
3. Render auto-detects `render.yaml`. Confirm the settings.
4. Set **Environment Variable** `OPENAI_API_KEY` (required).
5. Click **Deploy**. Render will:
   - Install dependencies
   - Run `bash boot.sh` (which ingests `./sample_data` and starts the API)
6. Your API will be available at: `https://<your-service>.onrender.com`

### Endpoint
- Health: `GET /health`
- RAG Answer: `POST /hrlaw/rag`
  - Body: `{ "question": "Is maternity leave 26 weeks?", "top_k": 5 }`

### Typebot HTTP Request settings
- Method: `POST`
- URL: `https://<your-service>.onrender.com/hrlaw/rag`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "question": "{{user_query}}",
  "session_id": "{{session.id}}"
}
```
- Map Response:
  - `ai_answer`  ← `response.answer`
  - `ai_sources` ← `response.sources`

**Note on persistence:** We attach a 1 GB **Persistent Disk** at `/var/data` for the Chroma DB (`DB_PATH=/var/data/ragdb`). Your index survives restarts/redeploys.
