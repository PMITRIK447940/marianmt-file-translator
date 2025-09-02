import subprocess
from pathlib import Path
from typing import List, Tuple, Dict

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

def _translate_blocks(blocks: List[str], src: str, tgt: str, max_chars: int = 6000) -> List[str]:
    tokenizer, model = _load_model(src, tgt)
    out: List[str] = []
    batch: List[str] = []
    total = 0
    def flush():
        nonlocal batch, out, total
        if not batch:
            return
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True)
        tokens = model.generate(**inputs, max_length=2048)
        out.extend(tokenizer.batch_decode(tokens, skip_special_tokens=True))
        batch = []
        total = 0
    for b in blocks:
        L = len(b)
        if total + L > max_chars:
            flush()
        batch.append(b)
        total += L
    flush()
    return out

def _split_text(text: str) -> List[str]:
    paras = [p.strip() for p in text.replace('\r\n', '\n').split('\n\n')]
    return [p for p in paras if p]

def translate_text(text: str, target_lang: str) -> Tuple[str, str]:
    if not text.strip():
        return '', 'unknown'
    try:
        src = detect(text[:2000]).lower()
    except Exception:
        src = 'en'
    tgt = target_lang.lower()
    if src == tgt:
        return text, src
    try:
        blocks = _split_text(text)
        out = _translate_blocks(blocks, src, tgt)
        return '\n\n'.join(out), src
    except Exception:
        pass
    if src != 'en' and tgt != 'en':
        blocks = _split_text(text)
        mid = _translate_blocks(blocks, src, 'en')
        out = _translate_blocks(mid, 'en', tgt)
        return '\n\n'.join(out), src
    raise RuntimeError(f'No model available for {src}->{tgt}')

def translate_document(src_path: Path, target_lang: str) -> Path:
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
    translated, _ = translate_text(text, target_lang=target_lang)

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
