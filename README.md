# MarianMT File Translator v2.4 — Visual progress (upload + translation)
New endpoints:
- POST /api/upload -> { job_id }
- GET /api/status/{job_id} -> phase/progress/done/error
- GET /api/download/{job_id} -> file

Frontend shows upload progress (XHR) and translation progress (polling).
15 MB limit, Railway PORT-aware Dockerfile, static under /static, GET /.
