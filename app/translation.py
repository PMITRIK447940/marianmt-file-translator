import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Callable, Optional

from langdetect import detect
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from .file_utils import read_text_from_any, write_text_to_docx

_MODEL_CACHE: Dict[Tuple[str, str], Tuple[AutoTokenizer, AutoModelForSeq2SeqLM]] = {}

def _load_model(src: str, tgt: str):
    key = (src, tgt)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    model_name = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    _MODEL_CACHE[key] = (tokenizer, model)
    return tokenizer, model

def _split_text(text: str) -> List[str]:
    return [p.strip() for p in text.replace('\r\n', '\n').split('\n\n') if p.strip()]

def _translate_blocks(blocks: List[str], src: str, tgt: str, hook: Optional[Callable[[int,int],None]]=None) -> List[str]:
    tokenizer, model = _load_model(src, tgt)
    out: List[str] = []
    batch: List[str] = []
    total = len(blocks)
    done = 0
    def flush():
        nonlocal batch, out, done
        if not batch:
            return
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True)
        tokens = model.generate(**inputs, max_length=2048)
        out.extend(tokenizer.batch_decode(tokens, skip_special_tokens=True))
        done += len(batch)
        if hook:
            hook(done, total)
        batch.clear()
    max_chars = 6000
    cur = 0
    for b in blocks:
        bl = len(b)
        if cur + bl > max_chars:
            flush()
            cur = 0
        batch.append(b)
        cur += bl
    flush()
    return out

def translate_text_with_progress(text: str, target_lang: str, progress_hook: Optional[Callable[[int,int],None]]=None) -> Tuple[str, str]:
    if not text.strip():
        return '', 'unknown'
    try:
        src = detect(text[:2000]).lower()
    except Exception:
        src = 'en'
    tgt = target_lang.lower()
    if src == tgt:
        return text, src
    blocks = _split_text(text)
    try:
        out = _translate_blocks(blocks, src, tgt, hook=progress_hook)
        return '\n\n'.join(out), src
    except Exception:
        pass
    if src != 'en' and tgt != 'en':
        mid = _translate_blocks(blocks, src, 'en', hook=None)
        out = _translate_blocks(mid, 'en', tgt, hook=progress_hook)
        return '\n\n'.join(out), src
    raise RuntimeError(f'No model available for {src}->{tgt}')

def translate_document_with_progress(src_path: Path, target_lang: str, progress_hook: Optional[Callable[[int,int],None]]=None) -> Path:
    suffix = src_path.suffix.lower()
    path_to_read = src_path
    if suffix == '.doc':
        tmp_dir = src_path.parent
        res = subprocess.run(['soffice', '--headless', '--convert-to', 'docx', str(src_path), '--outdir', str(tmp_dir)], capture_output=True)
        if res.returncode != 0:
            err = res.stderr.decode('utf-8', 'ignore')
            raise RuntimeError(f".doc conversion failed: {err}")
        path_to_read = src_path.with_suffix('.docx')
    text = read_text_from_any(path_to_read)
    translated, _ = translate_text_with_progress(text, target_lang=target_lang, progress_hook=progress_hook)
    out_dir = src_path.parent
    if suffix == '.txt':
        out_path = out_dir / f'{src_path.stem}_translated_{target_lang}.txt'
        out_path.write_text(translated, encoding='utf-8')
    elif suffix in ['.doc', '.docx', '.rtf']:
        out_path = out_dir / f'{src_path.stem}_translated_{target_lang}.docx'
        write_text_to_docx(translated, out_path)
    elif suffix == '.pdf':
        out_path = out_dir / f'{src_path.stem}_translated_{target_lang}.txt'
        out_path.write_text(translated, encoding='utf-8')
    else:
        raise RuntimeError(f'Unsupported extension: {suffix}')
    return out_path
