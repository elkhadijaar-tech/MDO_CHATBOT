"""Recherche v2 : BM25 + bigrammes, filtres par base, multi-requêtes, dédoublonnage, pondération qualité."""
import math
import re
from collections import Counter

from .aliases import expansions
from .textutil import GENERIC, normalize, tokenize

MIN_SCORE = 3.0
_SEM_PATTERNS = [
    (re.compile(r"(?<![a-z0-9])f?s([1-4])(?!\w)"), None),
    (re.compile(r"(?:semestre|semester|سداسي|الفصل)\s*([1-4])"), None),
    (re.compile(r"(?:premier|1er|first)\s+(?:semestre|semester)"), 1),
    (re.compile(r"(?:deuxieme|second|2eme|2nd)\s+(?:semestre|semester)"), 2),
    (re.compile(r"(?:troisieme|third|3eme|3rd)\s+(?:semestre|semester)"), 3),
    (re.compile(r"(?:quatrieme|fourth|4eme|4th)\s+(?:semestre|semester)"), 4),
]
_WHO = re.compile(r"(?<!\w)(qui|who|prof|profs|professeur|professeurs|enseigne|enseignant|teacher|teaches|chkoun|chkon|شكون|استاذ|الاستاذ|ostad|oustad|ustad)(?!\w)")
_SPLIT = re.compile(r"\s+(?:et|and|puis|ainsi que|ou encore|و)\s+|[;?]|,\s+")
QUALITY = {"VERIFIED_OFFICIAL": 1.0, "VERIFIED_USER_DATABASE": 1.0, "VERIFIED_SECONDARY": 0.95,
           "NEEDS_VERIFICATION": 0.9, "OUTDATED": 0.7, "CONFLICTING": 0.8, "UNAVAILABLE": 0.5}


def detect_semesters(query: str) -> list:
    q = normalize(query)
    found = []
    for pat, fixed in _SEM_PATTERNS:
        for m in pat.finditer(q):
            n = fixed if fixed else int(m.group(1))
            if n not in found:
                found.append(n)
    return found


def _name_variants(text: str) -> list:
    m = re.search(r"«\s*(.+?)\s*»", text)
    if not m:
        return []
    full = m.group(1)
    variants = [normalize(full)]
    plain = re.sub(r"\s*\(.*?\)", "", full).strip()
    if plain and normalize(plain) not in variants:
        variants.append(normalize(plain))
    for inner in re.findall(r"\((.*?)\)", full):
        if len(inner) >= 2 and not inner.lower().startswith("arabe"):
            variants.append(normalize(inner))
    return variants


def _with_bigrams(toks: list) -> list:
    return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]


def split_queries(query: str) -> list:
    """Questions composées -> sous-questions (au moins 2 mots utiles chacune), sinon liste vide."""
    parts = [p.strip() for p in _SPLIT.split(query) if p and p.strip()]
    good = [p for p in parts if len(tokenize(p)) >= 1]
    return good if len(good) >= 2 else []


class Index:
    def __init__(self, chunks: list):
        self.names, self.docs = {}, []
        df = Counter()
        for c in chunks:
            toks = _with_bigrams(tokenize(c["title"] + " " + c["text"]))
            self.docs.append((c, Counter(toks), len(toks)))
            df.update(set(toks))
            if c.get("kind") == "module":
                self.names[c["id"]] = _name_variants(c["text"])
        n = max(len(self.docs), 1)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.avgdl = sum(d[2] for d in self.docs) / n if self.docs else 1.0

    @property
    def size(self) -> int:
        return len(self.docs)

    def kb_counts(self) -> dict:
        return dict(Counter(c.get("kb", "onboarding") for c, _, _ in self.docs))

    def _score(self, weights: dict, tf: Counter, dl: int) -> float:
        k1, b, s = 1.5, 0.75, 0.0
        for tok, w in weights.items():
            f = tf.get(tok, 0)
            if f:
                s += w * self.idf.get(tok, 0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / self.avgdl))
        return s

    def _search_one(self, query: str, kbs=None) -> list:
        base = tokenize(query)
        exp = expansions(query)
        known = [t for t in base if t in self.idf]
        # hors-sujet : sans alias reconnu, trop de mots de la question sont inconnus de la base (ex. « capitale de la France »)
        if base and not exp.strip() and len(known) / len(base) < 0.6:
            return []
        weights = {t: 0.5 for t in _with_bigrams(tokenize(exp))}
        for t in _with_bigrams(base):
            weights[t] = 1.0
        sems = detect_semesters(query)
        specific = [t for t in base if t not in GENERIC and not re.fullmatch(r"s?[1-4]", t) and t in self.idf]
        nq = normalize(query)
        wants_prof = _WHO.search(nq) is not None
        scored = []
        for c, tf, dl in self.docs:
            if kbs and c.get("kb", "onboarding") not in kbs:
                continue
            sc = self._score(weights, tf, dl) * QUALITY.get(c.get("verification"), 0.9)
            if c.get("kind") == "module" and sc > 0:
                if wants_prof:
                    sc += 4
                if any(re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", nq) for v in self.names.get(c["id"], [])):
                    sc += 6
            if c.get("kind") == "semester" and c.get("semester") in sems:
                sc += 50 if not specific else 2
            scored.append((sc, c, tf))
        scored.sort(key=lambda x: -x[0])
        if not scored or scored[0][0] < MIN_SCORE:
            return []
        top = scored[0][0]
        if not exp.strip() and len(base) >= 2:
            need = max(2, -(-len(base) // 2))
            if sum(1 for t in set(base) if scored[0][2].get(t)) < need:
                return []  # le meilleur passage ne couvre qu'un seul mot : preuve insuffisante
        forced = [(x[0], x[1]) for x in scored if x[0] >= 50]
        return forced if forced else [(x[0], x[1]) for x in scored if x[0] >= max(MIN_SCORE, 0.65 * top)]

    def search(self, query: str, k: int = 4, kbs=None) -> list:
        subs = split_queries(query)
        merged = {}
        for q in [query] + subs:
            for sc, c in self._search_one(q, kbs):
                if c["id"] not in merged or sc > merged[c["id"]][0]:
                    merged[c["id"]] = (sc, c)
        ranked, seen = [], set()
        for sc, c in sorted(merged.values(), key=lambda x: -x[0]):
            key = " ".join(normalize(c["text"]).split())
            if key in seen:
                continue
            seen.add(key)
            ranked.append(dict(c, score=round(sc, 2)))
        return ranked[: k + (2 if subs else 0)]
