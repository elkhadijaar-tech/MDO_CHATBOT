"""Client LLM multi-fournisseurs (Anthropic, OpenAI, Gemini, API compatible OpenAI) : retries, usage, test de connexion."""
import threading
import time

import requests

RETRY_STATUS = {429, 500, 502, 503, 504, 529}
OPENAI_COMPATIBLE_BASE = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}
PROVIDERS = ("anthropic", "openai", "gemini", "openai-compatible")


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, provider, api_key, model, base_url="", retries=3, backoff=1.5, timeout=45, fallback_model=""):
        self.provider, self.api_key, self.model = provider, api_key, model
        self.base_url = base_url.rstrip("/")
        self.retries, self.backoff, self.timeout = retries, backoff, timeout
        self.fallback_model = fallback_model
        self._local = threading.local()
        self.verified = None  # None = jamais testé ; sinon dict {ok, ms, error, at}

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def last_usage(self) -> dict:
        return getattr(self._local, "usage", {})

    def _request(self, model, system, messages, max_tokens):
        if self.provider == "anthropic":
            url = (self.base_url or "https://api.anthropic.com") + "/v1/messages"
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
        else:
            base = self.base_url or OPENAI_COMPATIBLE_BASE.get(self.provider, "https://api.openai.com/v1")
            url = base + "/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"}
            body = {"model": model, "max_tokens": max_tokens, "temperature": 0.2,
                    "messages": [{"role": "system", "content": system}] + messages}
        return requests.post(url, headers=headers, json=body, timeout=self.timeout)

    def _generate(self, model, system, messages, max_tokens):
        last = "erreur inconnue"
        for attempt in range(self.retries):
            try:
                resp = self._request(model, system, messages, max_tokens)
            except requests.RequestException as exc:
                last = f"réseau : {exc.__class__.__name__}"
            else:
                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        if self.provider == "anthropic":
                            u = data.get("usage") or {}
                            self._local.usage = {"in": u.get("input_tokens"), "out": u.get("output_tokens")}
                            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text").strip()
                        u = data.get("usage") or {}
                        self._local.usage = {"in": u.get("prompt_tokens"), "out": u.get("completion_tokens")}
                        return data["choices"][0]["message"]["content"].strip()
                    except (KeyError, IndexError, TypeError) as exc:
                        raise LLMError("Réponse inattendue du fournisseur") from exc
                last = f"HTTP {resp.status_code}"
                if resp.status_code in (401, 403):
                    last += " (clé API refusée)"
                if resp.status_code not in RETRY_STATUS:
                    break
            if attempt < self.retries - 1:
                time.sleep(self.backoff * (2 ** attempt))
        raise LLMError(f"Échec de l'appel LLM ({last})")

    def generate(self, system: str, messages: list, max_tokens: int = 900) -> str:
        """Appelle le modèle principal. Retourne le texte ; le modèle utilisé est self.last_model."""
        if not self.configured:
            raise LLMError("Clé API absente")
        self._local.usage = {}
        try:
            text = self._generate(self.model, system, messages, max_tokens)
            self._local.model = self.model
            return text
        except LLMError:
            if not self.fallback_model:
                raise
            text = self._generate(self.fallback_model, system, messages, max_tokens)
            self._local.model = self.fallback_model  # signalé à l'interface : jamais de bascule silencieuse
            return text

    @property
    def last_model(self) -> str:
        return getattr(self._local, "model", self.model)

    def test_connection(self) -> dict:
        t0 = time.time()
        if not self.configured:
            res = {"ok": False, "error": "Aucune clé API configurée."}
        else:
            try:
                self._generate(self.model, "Réponds uniquement : ok", [{"role": "user", "content": "ping"}], 5)
                res = {"ok": True}
            except LLMError as exc:
                res = {"ok": False, "error": str(exc)}
        res["ms"] = int((time.time() - t0) * 1000)
        res["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.verified = res
        return res
