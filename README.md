# MarianMT File Translator v2.1 — 15 MB limit (FastAPI, Railway-ready)

- Max upload size: **15 MB** (middleware + server-side stream check).
- Formats in: **.pdf, .doc, .docx, .rtf, .txt**
- Outputs: `.txt` (for PDF) or `.docx` (for word-processor files), `.txt` for text files.
- Uses **Helsinki-NLP/opus-mt** (MarianMT) with pivot cez EN keď chýba priamy model.

## Local run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# http://127.0.0.1:8000
```

## Deploy to Railway (GitHub)
- Push this folder to GitHub
- Railway → New Project → Deploy from GitHub
- It builds the Dockerfile; open the public URL

## Notes
- `.doc` is converted via LibreOffice headless to `.docx` internally.
- PDF layout is not preserved — text extraction only.
- First-time model use downloads from Hugging Face; cold start can be longer.
