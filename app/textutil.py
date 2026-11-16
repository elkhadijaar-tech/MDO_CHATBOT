"""Normalisation et tokenisation (français, anglais, arabe)."""
import re
import unicodedata

_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})

STOPWORDS = set("""
le la les l un une des du de d et ou est sont que qui quoi quel quels quelle quelles ou comment je j mon ma mes
ton ta tes son sa ses dans pour sur au aux en a ce cet cette ces il elle ils elles on nous vous se si ne pas par
avec sans sous plus moins tres puis donc car mais y c s t m n qu cela ca peut faut dois doit faire fait
the is are of to in for how what where when can do does i my me an and or if it on at be there which who tell about please
am was were this that with from you your we our they their will would should could
genere generer generate cree creer create fais entrainement explique expliquer explain exemple exemples example donne donner give resume resumer summarize summary qcm quiz calcule calculer calculate peux pouvez peut veux voudrais svp stp plait pouvez dis dites tell
""".split())

GENERIC = set("""module modules semestre semester professeur prof enseigne enseignant liste list filiere mdo programme
estc quel quels quelle sont les etudiant etudiants""".split())


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ـ", "")
    text = text.translate(_AR_MAP)
    text = text.replace("’", "'")
    return text


def _stem(tok: str) -> str:
    if tok.startswith("ال") and len(tok) > 4:
        tok = tok[2:]
    if re.fullmatch(r"[a-z]+", tok) and len(tok) > 3 and tok[-1] in "sx":
        tok = tok[:-1]
    return tok


def tokenize(text: str, keep_stopwords: bool = False) -> list:
    toks = re.findall(r"\w+", normalize(text))
    if not keep_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    return [_stem(t) for t in toks if t]
