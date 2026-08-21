"""FastAPI backend for Xebia Proposal Studio."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from planner.proposal_planner import ProposalSession
from generation.template_engine import get_template_info

app = FastAPI(title="Xebia Proposal Studio", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"

sessions: dict[str, ProposalSession] = {}

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


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


class GenerateRequest(BaseModel):
    template_name: str | None = None
    formats: str = "both"  # "pptx" | "docx" | "both"


class GenerateResponse(BaseModel):
    session_id: str
    files: dict


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = STATIC_DIR / "index.html"
    return index_path.read_text(encoding="utf-8")


# ── Templates ────────────────────────────────────────────────

@app.get("/api/templates")
async def list_templates():
    return {"templates": get_template_info()}


# ── Chat ─────────────────────────────────────────────────────

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


# ── Generate ─────────────────────────────────────────────────

@app.post("/api/generate/{session_id}", response_model=GenerateResponse)
async def generate(session_id: str, req: GenerateRequest = None):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    if session.status != "plan_ready":
        raise HTTPException(400, "No proposal plan ready for generation")

    template_name = req.template_name if req else None
    formats = req.formats if req else "both"
    if formats not in ("pptx", "docx", "both"):
        raise HTTPException(400, "formats must be one of 'pptx', 'docx', 'both'")

    result = session.generate(template_name=template_name, formats=formats)
    return GenerateResponse(session_id=session_id, files=result)


# ── Download ─────────────────────────────────────────────────

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


# ── Image Upload ─────────────────────────────────────────────

@app.post("/api/upload/{session_id}")
async def upload_images(
    session_id: str,
    files: list[UploadFile] = File(...),
    image_type: str = Form("reference"),
):
    session = _get_or_create_session(session_id)
    if image_type not in ("reference", "embed"):
        raise HTTPException(400, "image_type must be 'reference' or 'embed'")

    session_dir = UPLOAD_DIR / session.session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for f in files:
        if f.content_type not in ALLOWED_IMAGE_TYPES:
            continue

        data = await f.read()
        if len(data) > MAX_IMAGE_SIZE:
            continue

        image_id = uuid.uuid4().hex[:12]
        ext = Path(f.filename).suffix or ".png"
        save_name = f"{image_id}{ext}"
        save_path = session_dir / save_name
        save_path.write_bytes(data)

        meta = {
            "id": image_id,
            "filename": f.filename,
            "path": str(save_path),
            "type": image_type,
            "mime_type": f.content_type,
            "size": len(data),
        }
        session.images.append(meta)
        uploaded.append(meta)

    return {"session_id": session.session_id, "uploaded": uploaded}


@app.get("/api/images/{session_id}")
async def list_images(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return {"images": sessions[session_id].images}


@app.get("/api/image/{session_id}/{image_id}")
async def get_image(session_id: str, image_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    for img in sessions[session_id].images:
        if img["id"] == image_id:
            path = Path(img["path"])
            if path.exists():
                return FileResponse(path, media_type=img["mime_type"])
    raise HTTPException(404, "Image not found")


# ── Session ──────────────────────────────────────────────────

@app.post("/api/reset")
async def reset_session():
    session = ProposalSession()
    sessions[session.session_id] = session
    return {"session_id": session.session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
