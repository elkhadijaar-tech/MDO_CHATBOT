"""Détection simple de la langue de l'étudiant : fr, en, ar, darija."""
import re
from .textutil import normalize

LANGS = ("fr", "en", "ar", "darija")

_DARIJA_AR = {normalize(w) for w in """كيفاش فين شنو علاش واش ديال ديالي ديالو ديالهم بغيت بغينا مزيان دابا كاين كاينة ماشي بزاف
واخا شحال بشحال فاش امتى منين عندي غادي نقدر كنقدر علاه شكون فاين لاباس هاد هادا هادي""".split()}

_DARIJA_LAT = set("""kifach kifash wach chno chnou shno bghit bghina alach dyal dial mchi daba kayn kayna machi bzaf wakha
chhal bchhal fach imta mnin hna hnaya labas mzyan mzian chkoun chkon 3afak afak safi nta nti ghadi ghadi kaynin
kandir ndir nqdr nqder wach""".split())

_FR = set("""le la les de des du un une et est que qui quoi comment je mon ma mes dans pour sur au aux ce ces il elle nous
vous ou où quel quels quelle quelles quand pourquoi avec sans bonjour merci salut est-ce""".replace("-", " ").split())
_EN = set("""the is are of to in for how what where when can do does i my me an and or if it on at there which who tell
about please hello thanks hi would should could you your""".split())

_ARABIZI = re.compile(r"\b[a-z]*[379][a-z]+\b|\b[a-z]+[379][a-z]*\b")


def detect_language(text: str) -> str:
    t = text.strip()
    arabic = len(re.findall(r"[\u0600-\u06FF]", t))
    latin = len(re.findall(r"[A-Za-z]", t))
    words = set(re.findall(r"\w+", normalize(t)))
    if arabic > latin:
        return "darija" if words & _DARIJA_AR else "ar"
    if words & _DARIJA_LAT or len(_ARABIZI.findall(t.lower())) >= 1:
        # un seul mot arabizi suffit quand il contient un chiffre au milieu d'un mot latin
        return "darija"
    fr = len(words & {normalize(w) for w in _FR})
    en = len(words & _EN)
    return "en" if en > fr else "fr"
