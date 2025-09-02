# MarianMT File Translator v2.2 — 15 MB limit + Railway PORT fix

- Fix: f-string v `translation.py` (bez spätných lomítok v expression).
- Dockerfile spúšťa Uvicorn na `${PORT}` (Railway štandard).
- 15 MB upload limit cez middleware + stream check.
- Formáty: .pdf, .doc, .docx, .rtf, .txt. Výstup: `.docx` (word), `.txt` (pdf/txt).

## Run locally
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

## Deploy to Railway (GitHub)
- Push to repo → Deploy from GitHub
- Logs: Deployments → Logs
- Health: GET /health

Notes: .doc → .docx cez LibreOffice; PDF je plain text; prvý preklad daného páru stiahne model.
