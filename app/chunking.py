"""Découpage de texte en passages en respectant titres, tableaux et blocs de code."""
import hashlib
import re

from .textutil import normalize

MAX_CHARS = 900
MIN_CHARS = 200


def text_hash(text: str) -> str:
    return hashlib.sha256(" ".join(normalize(text).split()).encode("utf-8")).hexdigest()


def _blocks(lines):
    """Regroupe les lignes en blocs atomiques : tableau, bloc de code, ou ligne/paragraphe."""
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith("```"):
            j = i + 1
            while j < n and not lines[j].strip().startswith("```"):
                j += 1
            yield "\n".join(lines[i:j + 1]), "code"
            i = j + 1
        elif line.strip().startswith("|"):
            j = i
            while j < n and lines[j].strip().startswith("|"):
                j += 1
            yield "\n".join(lines[i:j]), "table"
            i = j
        elif line.strip():
            yield line.strip(), "text"
            i += 1
        else:
            i += 1


def chunk_markdown(text: str, default_title: str = "", max_chars: int = MAX_CHARS, min_chars: int = MIN_CHARS,
                   overlap: int = 0) -> list:
    """Retourne [{'heading': str, 'text': str}] ; le titre (#, ##, ###) est conservé pour chaque passage."""
    chunks, heading, buf = [], default_title, []

    def flush():
        if buf:
            chunks.append({"heading": heading, "text": "\n".join(buf).strip()})
            buf.clear()

    def size():
        return sum(len(b) for b in buf)

    lines = text.splitlines()
    for block, kind in _blocks(lines):
        m = re.match(r"^(#{1,6})\s+(.*)", block) if kind == "text" else None
        if m:
            flush()
            heading = m.group(2).strip()
            continue
        if kind in ("table", "code"):
            if size() >= min_chars:
                flush()
            buf.append(block)
            flush()
            continue
        if size() + len(block) > max_chars and size() >= min_chars:
            tail = buf[-1][-overlap:] if overlap and buf else ""
            flush()
            if tail:
                buf.append(tail)
        buf.append(block)
        if len(block) > max_chars:  # paragraphe très long : coupe aux phrases
            flush()
    flush()
    out = []
    for c in chunks:
        t = c["text"]
        if len(t) <= max_chars * 1.6:
            out.append(c)
            continue
        parts, cur = re.split(r"(?<=[.;!?])\s+", t), ""
        for p in parts:
            if len(cur) + len(p) > max_chars and cur:
                out.append({"heading": c["heading"], "text": cur.strip()})
                cur = ""
            cur += p + " "
        if cur.strip():
            out.append({"heading": c["heading"], "text": cur.strip()})
    return [c for c in out if c["text"]]
