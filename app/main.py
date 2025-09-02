import os
from pathlib import Path
import fastapi
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .translation import translate_document
from .languages import SUPPORTED_LANGS

MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        try:
            if cl and int(cl) > MAX_UPLOAD_SIZE:
                return JSONResponse(
                    {"detail": f"File too large. Max {MAX_UPLOAD_SIZE // (1024*1024)} MB allowed."},
                    status_code=413,
                )
        except Exception:
            pass
        return await call_next(request)

app = FastAPI(title="MarianMT File Translator v2.2 (15MB, Railway PORT)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Upload size limiter
app.add_middleware(LimitUploadSizeMiddleware)

# Frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/languages")
def get_languages():
    return [{"code": code, "name": name} for name, code in SUPPORTED_LANGS.items()]

@app.post("/api/translate")
async def translate_api(
    file: UploadFile = File(...),
    target_lang: str = Form(...),
):
    if not target_lang:
        raise HTTPException(status_code=400, detail="Missing target_lang")

    suffix = Path(file.filename).suffix.lower()
    valid_exts = {".txt", ".doc", ".docx", ".pdf", ".rtf"}
    if suffix not in valid_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    # Save stream to disk with secondary size enforcement
    tmpdir = Path("/tmp")
    tmpdir.mkdir(parents=True, exist_ok=True)
    src_path = tmpdir / f"upload_{os.getpid()}_{file.filename}"
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

    try:
        out_path = translate_document(src_path, target_lang=target_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

    return FileResponse(path=str(out_path), media_type="application/octet-stream", filename=out_path.name)
