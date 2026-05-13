import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import papers, illustrations, chat, literature

app = FastAPI(title="Paper Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(illustrations.router)
app.include_router(chat.router)
app.include_router(literature.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
