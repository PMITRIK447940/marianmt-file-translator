async function loadLanguages() {
  const sel = document.getElementById('target_lang');
  const info = document.getElementById('langStatus');
  try {
    const resp = await fetch('/api/languages');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const langs = await resp.json();
    langs.forEach(({ code, name }) => {
      const opt = document.createElement('option');
      opt.value = code;
      opt.textContent = `${name} (${code})`;
      sel.appendChild(opt);
    });
    for (let i=0;i<sel.options.length;i++){ if(sel.options[i].value==='sk'){ sel.selectedIndex=i; break; } }
    info.textContent = '';
  } catch (e) {
    info.textContent = 'Failed to load languages. Check /api/languages and server logs.';
    console.error('loadLanguages error:', e);
  }
}

function show(el){ el.classList.remove('hidden'); }
function hide(el){ el.classList.add('hidden'); }

function setBar(bar, pctEl, val){
  const pct = Math.max(0, Math.min(100, Math.round(val)));
  bar.style.width = pct + '%';
  pctEl.textContent = pct + '%';
}

async function submitForm(e){
  e.preventDefault();

  const progressArea = document.getElementById('progressArea');
  const uploadBar = document.getElementById('uploadBar');
  const uploadPct = document.getElementById('uploadPct');
  const transBar = document.getElementById('transBar');
  const transPct = document.getElementById('transPct');
  const status = document.getElementById('status');
  const downloadArea = document.getElementById('downloadArea');
  const downloadBtn = document.getElementById('downloadBtn');

  show(progressArea);
  hide(downloadArea);
  setBar(uploadBar, uploadPct, 0);
  setBar(transBar, transPct, 0);
  status.textContent = 'Starting upload...';

  const form = document.getElementById('tform');
  const fd = new FormData(form);

  const xhr = new XMLHttpRequest();
  const uploadPromise = new Promise((resolve, reject) => {
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const pct = (e.loaded / e.total) * 100;
        setBar(uploadBar, uploadPct, pct);
        status.textContent = 'Uploading...';
      }
    });
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.responseText);
      else reject(new Error('Upload failed: HTTP ' + xhr.status + ' ' + xhr.responseText));
    });
    xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
    xhr.open('POST', '/api/upload');
    xhr.send(fd);
  });

  let job;
  try {
    const txt = await uploadPromise;
    job = JSON.parse(txt);
    setBar(uploadBar, uploadPct, 100);
    status.textContent = 'Upload complete. Translating...';
  } catch (err) {
    status.textContent = err.message || String(err);
    return;
  }

  const jobId = job.job_id;
  const poll = async () => {
    const r = await fetch('/api/status/' + jobId);
    if (!r.ok) throw new Error('Status HTTP ' + r.status);
    const s = await r.json();
    setBar(transBar, transPct, s.progress || 0);
    if (s.phase === 'error') {
      throw new Error(s.error || 'Translation failed');
    }
    if (s.done) return true;
    return false;
  };

  try {
    let done = false;
    while (!done) {
      done = await poll();
      await new Promise(res => setTimeout(res, 1000));
    }
    status.textContent = 'Translation complete!';
    show(downloadArea);
    downloadBtn.href = '/api/download/' + jobId;
  } catch (e) {
    status.textContent = e.message || String(e);
  }
}

document.getElementById('tform').addEventListener('submit', submitForm);
window.addEventListener('DOMContentLoaded', loadLanguages);
