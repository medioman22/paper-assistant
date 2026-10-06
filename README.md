# Paper Assistant

Upload a research paper (PDF) and get a structured summary, a chat that cites the paper, generated illustrations, and related-paper recommendations grounded in Google Scholar.

- **Backend:** FastAPI (Python 3.11) in `backend/`, using Gemini.
- **Frontend:** React + Vite + TypeScript in `frontend/`.

## Requirements

- Python 3.11 (`backend/requirements.txt`)
- Node 22 (`.nvmrc`)
- A Gemini API key

## Setup

```bash
# backend
cd backend
python3.11 -m venv .venv            # or: uv venv --python 3.11 .venv
.venv/bin/pip install -r requirements.txt   # or: uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env                # then fill in GEMINI_API_KEY

# frontend
cd ../frontend
npm ci
```

## Run

```bash
./dev.sh    # starts backend (port 18000) and frontend (port 15173), stops both on Ctrl-C
```

Sessions, uploaded PDFs and generated images are stored in `backend/app/data/` and are not committed.

## Tests

```bash
cd backend && .venv/bin/pip install pytest && .venv/bin/pytest
```
