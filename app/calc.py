"""Calculs déterministes du cours (TVA, intérêts simples/composés, escompte commercial), avec étapes.

Le programme n'effectue un calcul que si toutes les données nécessaires sont présentes sans ambiguïté ;
sinon il retourne None et la question suit le circuit normal (explication du cours).
"""
import re

from .textutil import normalize

_NUM = r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
_RATE = re.compile(rf"({_NUM})\s*(?:%|pour ?cent|percent)")
_DUR = re.compile(rf"({_NUM})\s*(ans?|annees?|years?|yrs?|mois|months?|jours?|days?)\b")
_MONEY = re.compile(rf"({_NUM})\s*(?:dh|mad|dirhams?|€|eur|euros?|\$|usd)(?![a-z])")

LABELS = {
    "fr": {"calc": "Calcul", "formula": "formule du cours", "result": "Résultat", "note": "Calcul exécuté par le programme (pas par l'IA), avec les formules du cours.", "dec": ","},
    "en": {"calc": "Calculation", "formula": "course formula", "result": "Result", "note": "Computed by the program (not by the AI), using the course formulas.", "dec": "."},
    "ar": {"calc": "حساب", "formula": "صيغة الدرس", "result": "النتيجة", "note": "الحساب منفّذ بواسطة البرنامج (وليس الذكاء الاصطناعي) باستعمال صيغ الدرس.", "dec": ","},
}
LABELS["darija"] = LABELS["ar"]
SOURCES = {"tva": "Cours — 2. Financial Accounting (Comptabilité Générale)",
           "fin": "Cours — 6. Applied Mathematics & Financial Mathematics (Mathématiques Appliquées et Financières)"}


def _f(s: str) -> float:
    return float(re.sub(r"[ \u00a0\u202f]", "", s).replace(",", "."))


def fmt(x: float, lang: str) -> str:
    s = f"{x:,.2f}"
    if LABELS.get(lang, LABELS["fr"])["dec"] == ",":
        s = s.replace(",", " ").replace(".", ",")
    return s


def _extract(text: str):
    rates = [(_f(m.group(1)), m.span()) for m in _RATE.finditer(text)]
    durs = [(_f(m.group(1)), m.group(2), m.span()) for m in _DUR.finditer(text)]
    money = [(_f(m.group(1)), m.span()) for m in _MONEY.finditer(text)]
    masked = text
    for span in [r[1] for r in rates] + [d[2] for d in durs] + [m[1] for m in money]:
        masked = masked[:span[0]] + " " * (span[1] - span[0]) + masked[span[1]:]
    others = [_f(m.group(0)) for m in re.finditer(_NUM, masked)]
    amounts = [m[0] for m in money] or others
    return rates, durs, amounts


def num(x: float, lang: str) -> str:
    s = f"{x:g}"
    return s.replace(".", ",") if LABELS.get(lang, LABELS["fr"])["dec"] == "," else s


def _unit(u: str) -> str:
    if u.startswith(("an", "year", "yr")) or u.startswith("annee"):
        return "y"
    if u.startswith(("mois", "month")):
        return "m"
    return "d"


def try_calc(question: str, lang: str = "fr"):
    t = normalize(question)
    L = LABELS.get(lang, LABELS["fr"])
    rates, durs, amounts = _extract(t)
    if len(rates) != 1:
        return None
    rate = rates[0][0] / 100
    r_txt = f"{num(rates[0][0], lang)} %"

    def out(title, formula, lines, result_lines, kind):
        body = [f"**{L['calc']} — {title}** ({L['formula']} : {formula})"] + [f"- {x}" for x in lines]
        body += [f"**{L['result']} :**"] + [f"- {x}" for x in result_lines] + ["", f"_{L['note']}_"]
        return {"answer": "\n".join(body), "kind": kind, "source": SOURCES["tva" if kind.startswith("tva") else "fin"]}

    if re.search(r"(?<!\w)(tva|vat)(?!\w)", t) and re.search(r"(?<!\w)(ht|ttc)(?!\w)|hors taxe|toutes taxes", t):
        if len(amounts) != 1:
            return None
        a = amounts[0]
        has_ttc = re.search(r"(?<!\w)ttc(?!\w)|toutes taxes", t)
        has_ht = re.search(r"(?<!\w)ht(?!\w)|hors taxe", t)
        if has_ttc and has_ht:
            # les deux mots apparaissent : on retient celui qui suit immédiatement le montant, sinon celui qui le précède
            mm = _MONEY.search(t) or re.search(_NUM, t)
            after = re.search(r"(?<!\w)(ht|ttc)(?!\w)", t[mm.end():mm.end() + 14]) if mm else None
            before = re.search(r"(?<!\w)(ht|ttc)(?!\w)", t[max(0, mm.start() - 14):mm.start()]) if mm else None
            pick = after or before
            if not pick:
                return None
            has_ttc, has_ht = (pick.group(1) == "ttc"), (pick.group(1) == "ht")
        if has_ht:
            tva, ttc = a * rate, a * (1 + rate)
            return out("TVA", "TVA = HT × taux ; TTC = HT × (1 + taux)",
                       [f"HT = {fmt(a, lang)} ; taux = {r_txt}"],
                       [f"TVA = {fmt(a, lang)} × {num(rate, lang)} = {fmt(tva, lang)}", f"TTC = {fmt(a, lang)} × (1 + {num(rate, lang)}) = {fmt(ttc, lang)}"], "tva_ht")
        ht = a / (1 + rate)
        return out("TVA", "HT = TTC / (1 + taux) ; TVA = TTC − HT",
                   [f"TTC = {fmt(a, lang)} ; taux = {r_txt}"],
                   [f"HT = {fmt(a, lang)} / (1 + {num(rate, lang)}) = {fmt(ht, lang)}", f"TVA = {fmt(a, lang)} − {fmt(ht, lang)} = {fmt(a - ht, lang)}"], "tva_ttc")

    if len(amounts) != 1 or len(durs) != 1:
        return None
    a, (n, unit_txt, _) = amounts[0], durs[0]
    u = _unit(unit_txt)
    if "interet" in t and "compos" in t:
        years = n if u == "y" else (n / 12 if u == "m" else n / 365)
        if u != "y":
            return None  # le cours définit les intérêts composés par périodes annuelles
        cn = a * (1 + rate) ** years
        return out("intérêts composés", "Cn = C0 (1 + t)^n",
                   [f"C0 = {fmt(a, lang)} ; t = {r_txt} ; n = {num(n, lang)} an(s)"],
                   [f"Cn = {fmt(a, lang)} × (1 + {num(rate, lang)})^{num(n, lang)} = {fmt(cn, lang)}", f"Intérêts = Cn − C0 = {fmt(cn - a, lang)}"], "interets_composes")
    if "interet" in t and "simple" in t:
        if u == "y":
            i, expr = a * rate * n, f"I = {fmt(a, lang)} × {num(rate, lang)} × {num(n, lang)}"
        elif u == "m":
            i, expr = a * rate * n / 12, f"I = ({fmt(a, lang)} × {num(rate, lang)} × {num(n, lang)}) / 12"
        else:
            i, expr = a * rate * n / 360, f"I = ({fmt(a, lang)} × {num(rate, lang)} × {num(n, lang)}) / 360"
        return out("intérêts simples", "I = C0 × t × n ; mois : /12 ; jours : /360",
                   [f"C0 = {fmt(a, lang)} ; t = {r_txt} ; durée = {num(n, lang)} {unit_txt}"],
                   [f"{expr} = {fmt(i, lang)}", f"Cn = C0 + I = {fmt(a + i, lang)}"], "interets_simples")
    if "escompte" in t and "commercial" in t and u == "d":
        e = a * rate * n / 360
        return out("escompte commercial", "e = (V × t × j) / 360 ; a = V − e",
                   [f"V = {fmt(a, lang)} ; t = {r_txt} ; j = {num(n, lang)} jours"],
                   [f"e = ({fmt(a, lang)} × {num(rate, lang)} × {num(n, lang)}) / 360 = {fmt(e, lang)}", f"a = V − e = {fmt(a - e, lang)}"], "escompte")
    return None
