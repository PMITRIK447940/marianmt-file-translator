async function loadLanguages() {
  const sel = document.getElementById('target_lang');
  const info = document.getElementById('langStatus');
  try {
    const resp = await fetch('/api/languages');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const langs = await resp.json();
    if (!Array.isArray(langs) || langs.length === 0) {
      info.textContent = 'No languages returned from API.';
      return;
    }
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
async function submitForm(e){
  e.preventDefault();
  const status = document.getElementById('status');
  status.textContent = 'Uploading & translating (≤15 MB)...';
  const fd = new FormData(document.getElementById('tform'));
  const resp = await fetch('/api/translate',{method:'POST', body:fd});
  if(!resp.ok){
    let msg = resp.statusText;
    try { const j = await resp.json(); if(j.detail) msg = j.detail; } catch(e){}
    status.textContent = 'Error: ' + msg;
    return;
  }
  const blob = await resp.blob();
  const cd = resp.headers.get('Content-Disposition') || '';
  let filename = 'translated';
  const m = cd.match(/filename="?([^\"]+)"?/i);
  if(m) filename = m[1];
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  status.textContent = 'Done!';
}
document.getElementById('tform').addEventListener('submit', submitForm);
window.addEventListener('DOMContentLoaded', loadLanguages);
