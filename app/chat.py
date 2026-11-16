"""Orchestration v2 : langue -> règles fixes -> calcul -> contexte de conversation -> recherche multi-bases -> réponse."""
import re
import time

from .aliases import is_price_question, small_talk
from .calc import try_calc
from .lang import detect_language
from .llm import LLMClient, LLMError
from .messages import t
from .prompts import GENERATIVE, build_system, detect_task, trim_history
from .retrieval import Index
from .textutil import normalize, tokenize

_FOLLOW = re.compile(
    r"^(et |and |mais |donc |alors |encore|continue|suite|plus de|davantage|en detail|developpe|precise|reformule|"
    r"simplifie|un autre|une autre|another|more|go on|same|meme chose|pareil|compare|et pour|et si|"
    r"et (la|le|les)\b|pourquoi|comment ca|ca veut dire|cela veut dire|why|how so|"
    r"زيد|كمل|وماذا|و ال)|(?<!\w)(ca|cela|celui|celle|ceux|ce dernier|precedent|precedente|plus haut|ci-dessus|previous|above|"
    r"this|that|it|them)(?!\w)")


def _format_extract(chunks: list) -> str:
    seen, lines = set(), []
    for c in chunks:
        if c["text"] in seen:
            continue
        seen.add(c["text"])
        lines.append("• " + re.sub(r"^-\s+", "", c["text"]))
    return "\n".join(lines)


def _titles(chunks: list) -> list:
    out, seen = [], set()
    for c in chunks:
        if c["title"] not in seen:
            seen.add(c["title"])
            out.append(c["title"])
    return out


def _details(chunks: list) -> list:
    return [{"title": c["title"], "location": c.get("location"), "kb": c.get("kb"), "verification": c.get("verification"),
             "source": c.get("source_name")} for c in chunks]


def is_followup(question: str) -> bool:
    """Marqueurs explicites de question de suivi (« et pour… », « continue », « ça »…)."""
    return bool(_FOLLOW.search(normalize(question).strip()))


def contextualize(question: str, history: list) -> str:
    """Pour une question de suivi (« et pour la SA ? », « un exemple »), complète la requête avec la question précédente."""
    if not history or not is_followup(question):
        return question
    prev = [h["content"] for h in history if h["role"] == "user"][-2:]
    return " ".join(prev + [question]) if prev else question


class ChatEngine:
    def __init__(self, index: Index, llm: LLMClient):
        self.index, self.llm = index, llm

    def set_index(self, index: Index) -> None:
        self.index = index

    @property
    def mode(self) -> str:
        return "ia" if self.llm.configured else "demo"

    def answer(self, question: str, history: list, lang_pref: str = "auto", mode_pref: str = "auto") -> dict:
        t0 = time.time()
        lang = detect_language(question) if lang_pref in ("", "auto", None) else lang_pref
        base = {"language": lang, "sources": [], "source_details": [], "mode": "regle", "kb": None, "model": None,
                "usage": {}, "task": None, "retrieval_ms": 0, "llm_ms": 0, "chunks": 0}
        talk = small_talk(question)
        if talk:
            return dict(base, answer=t(talk, lang))
        calc = try_calc(question, lang)
        if calc:
            return dict(base, answer=calc["answer"], mode="calcul", sources=[calc["source"]], kb="cours",
                        source_details=[{"title": calc["source"], "kb": "cours", "verification": "VERIFIED_USER_DATABASE"}],
                        task="calcul")
        if is_price_question(question):
            return dict(base, answer=t("price", lang))
        query = contextualize(question, history)
        kbs = {"cours": ["cours"], "admin": ["onboarding"]}.get(mode_pref)
        r0 = time.time()
        chunks = self.index.search(query, kbs=kbs)
        if not chunks and history and query == question:
            # question courte sans marqueur (« donne un exemple ») : on réessaie avec la question précédente
            prev = [h["content"] for h in history if h["role"] == "user"][-2:]
            if prev:
                chunks = self.index.search(" ".join(prev + [question]), kbs=kbs)
        retrieval_ms = int((time.time() - r0) * 1000)
        if not chunks:
            return dict(base, answer=t("not_found", lang), not_found=True, retrieval_ms=retrieval_ms)
        top_kb = chunks[0].get("kb", "onboarding")
        kind = "admin" if top_kb == "onboarding" else "course"
        task = detect_task(question)
        meta = dict(base, sources=_titles(chunks), source_details=_details(chunks), kb=top_kb, task=task,
                    retrieval_ms=retrieval_ms, chunks=len(chunks))
        if not self.llm.configured:
            head = t("needs_ai", lang) if task in GENERATIVE else t("demo_intro", lang)
            return dict(meta, answer=head + "\n" + _format_extract(chunks), mode="demo")
        kept, summary = trim_history(history)
        system = build_system(kind, chunks, task, lang, summary)
        l0 = time.time()
        try:
            text = self.llm.generate(system, self._messages(kept, question))
        except LLMError:
            return dict(meta, answer=t("llm_down", lang) + "\n" + _format_extract(chunks), mode="demo_secours",
                        llm_ms=int((time.time() - l0) * 1000))
        return dict(meta, answer=text, mode="ia", model=self.llm.last_model, usage=self.llm.last_usage,
                    llm_ms=int((time.time() - l0) * 1000))

    @staticmethod
    def _messages(history: list, question: str) -> list:
        msgs = []
        for h in history[-8:]:
            role = "assistant" if h["role"] == "assistant" else "user"
            if msgs and msgs[-1]["role"] == role:
                msgs[-1]["content"] += "\n" + h["content"]
            else:
                msgs.append({"role": role, "content": h["content"]})
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        if msgs and msgs[-1]["role"] == "user":
            msgs[-1]["content"] += "\n" + question
        else:
            msgs.append({"role": "user", "content": question})
        return msgs
