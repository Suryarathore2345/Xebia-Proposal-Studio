"""FastAPI backend for Xebia Proposal Studio."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from planner.proposal_planner import ProposalSession

app = FastAPI(title="Xebia Proposal Studio", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

sessions: dict[str, ProposalSession] = {}


def _get_or_create_session(session_id: str | None) -> ProposalSession:
    if session_id and session_id in sessions:
        return sessions[session_id]
    session = ProposalSession()
    sessions[session.session_id] = session
    return session


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    ready: bool
    message: str
    plan_summary: dict | None = None


class GenerateResponse(BaseModel):
    session_id: str
    files: dict


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = STATIC_DIR / "index.html"
    return index_path.read_text(encoding="utf-8")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session = _get_or_create_session(req.session_id)
    result = session.chat(req.message)

    return ChatResponse(
        session_id=session.session_id,
        ready=result.get("ready", False),
        message=result.get("message", ""),
        plan_summary=result.get("plan_summary"),
    )


@app.post("/api/generate/{session_id}", response_model=GenerateResponse)
async def generate(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    if session.status != "plan_ready":
        raise HTTPException(400, "No proposal plan ready for generation")

    result = session.generate()
    return GenerateResponse(session_id=session_id, files=result)


@app.get("/api/download/{session_id}/{format}")
async def download(session_id: str, format: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    file_path = session.generated_files.get(format)

    if not file_path or not Path(file_path).exists():
        raise HTTPException(404, f"No {format} file generated")

    media_types = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    return FileResponse(
        path=file_path,
        media_type=media_types.get(format, "application/octet-stream"),
        filename=Path(file_path).name,
    )


@app.post("/api/reset")
async def reset_session():
    session = ProposalSession()
    sessions[session.session_id] = session
    return {"session_id": session.session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
