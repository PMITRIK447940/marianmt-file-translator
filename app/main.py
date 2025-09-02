import os
import uuid
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .translation import translate_document_with_progress
from .languages import SUPPORTED_LANGS

MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB
TMP_DIR = Path("/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

def set_job(job_id: str, data: Dict[str, Any]):
    with JOBS_LOCK:
        JOBS[job_id] = {**JOBS.get(job_id, {}), **data}

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with JOBS_LOCK:
        return JOBS.get(job_id)

app = FastAPI(title="MarianMT File Translator v2.4 (Progress, 15MB, Railway)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        try:
            if cl and int(cl) > MAX_UPLOAD_SIZE:
                return JSONResponse({"detail": f"File too large. Max {MAX_UPLOAD_SIZE // (1024*1024)} MB allowed."}, status_code=413)
        except Exception:
            pass
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/languages")
def get_languages():
    return [{"code": code, "name": name} for name, code in SUPPORTED_LANGS.items()]

@app.post("/api/upload")
async def upload_and_start(file: UploadFile = File(...), target_lang: str = Form(...)):
    if not target_lang:
        raise HTTPException(status_code=400, detail="Missing target_lang")

    suffix = Path(file.filename).suffix.lower()
    valid_exts = {".txt", ".doc", ".docx", ".pdf", ".rtf"}
    if suffix not in valid_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    src_path = TMP_DIR / f"upload_{os.getpid()}_{uuid.uuid4().hex}{suffix}"
    size = 0
    with open(src_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large. Max 15 MB allowed.")
            f.write(chunk)

    job_id = uuid.uuid4().hex
    set_job(job_id, {"phase": "queued", "progress": 0, "filename": Path(file.filename).name, "target_lang": target_lang, "src_path": str(src_path), "out_path": None, "error": None})

    def worker():
        set_job(job_id, {"phase": "translating", "progress": 0})
        try:
            def hook(done, total):
                pct = int((done / max(total, 1)) * 100)
                set_job(job_id, {"progress": pct})
            out_path = translate_document_with_progress(Path(src_path), target_lang=target_lang, progress_hook=hook)
            set_job(job_id, {"phase": "done", "progress": 100, "out_path": str(out_path)})
        except Exception as e:
            set_job(job_id, {"phase": "error", "error": str(e)})

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return {"phase": job.get("phase"), "progress": job.get("progress", 0), "filename": job.get("filename"), "error": job.get("error"), "done": job.get("phase") == "done"}

@app.get("/api/download/{job_id}")
def job_download(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job id")
    if job.get("phase") != "done" or not job.get("out_path"):
        raise HTTPException(status_code=409, detail="Job not finished")
    p = Path(job["out_path"])
    if not p.exists():
        raise HTTPException(status_code=410, detail="Output missing")
    return FileResponse(str(p), media_type="application/octet-stream", filename=p.name)
