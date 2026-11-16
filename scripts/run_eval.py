"""Évaluation reproductible : exécute tests/eval/dataset.json sur une ou deux versions de l'application.

Usage :  python scripts/run_eval.py [--baseline CHEMIN_V1] [--out docs/BENCHMARK.md]
Sans clé API, seule l'infrastructure est mesurée (recherche, règles, calculs, contexte) : aucun score de qualité de modèle
n'est inventé. Un test « passe » si TOUS les extraits attendus figurent dans la réponse (sans tenir compte des accents/casse).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def single(app_path, dataset):
    sys.path.insert(0, app_path)
    os.chdir(app_path)
    from app import create_app  # noqa: E402
    d = Path(tempfile.mkdtemp())
    app = create_app({"DB_PATH": d / "e.db", "LOG_DIR": d / "l", "UPLOAD_DIR": d / "u", "LLM_API_KEY": "", "ADMIN_PASSWORD": ""})
    eng = app.extensions["engine"]
    res = []
    for c in dataset["cases"]:
        t0 = time.time()
        r = eng.answer(c["question"], c.get("history", []), "auto")
        ms = (time.time() - t0) * 1000
        ans = r["answer"]
        ok = all(norm(e) in norm(ans) for e in c["expect_all"])
        if c.get("expect_no_sources"):
            ok = ok and not r.get("sources")
        res.append({"id": c["id"], "ok": ok, "ms": round(ms, 1), "mode": r.get("mode"), "answer": ans[:160].replace("\n", " ")})
    print(json.dumps(res, ensure_ascii=False))


def run(path, dataset_path):
    out = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--single", path, "--dataset", dataset_path],
                         capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        raise SystemExit(out.stderr[-2000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline"); ap.add_argument("--single"); ap.add_argument("--out", default=str(ROOT / "docs" / "BENCHMARK.md"))
    ap.add_argument("--dataset", default=str(ROOT / "tests" / "eval" / "dataset.json"))
    a = ap.parse_args()
    dataset = json.loads(Path(a.dataset).read_text(encoding="utf-8"))
    if a.single:
        return single(a.single, dataset)
    new = run(str(ROOT), a.dataset)
    old = run(a.baseline, a.dataset) if a.baseline else None
    cats = {}
    for c in dataset["cases"]:
        cats.setdefault(c["category"], []).append(c["id"])
    by_id = {r["id"]: r for r in new}
    old_id = {r["id"]: r for r in old} if old else {}
    L = ["# Benchmark MDO CHATBOT", "", f"Jeu de test : `tests/eval/dataset.json` ({len(dataset['cases'])} questions). Généré par `scripts/run_eval.py` le {time.strftime('%Y-%m-%d')}.", "",
         "**Ce que mesure ce benchmark :** l'infrastructure (recherche, règles de sécurité, calculs, prise en compte du contexte), exécutée **sans clé API** (mode démo). "
         "Un test est réussi si tous les extraits attendus figurent dans la réponse. **Il ne mesure pas la qualité rédactionnelle d'un modèle d'IA** : aucun score de ce type n'est annoncé, car aucun appel réel à un modèle n'a été fait.", ""]
    hdr = "| Catégorie | Questions | " + ("v1 (avant) | " if old else "") + "v2 (après) |"
    L += [hdr, "|---|---|" + ("---|" if old else "") + "---|"]
    tot_o = tot_n = 0
    for cat, ids in cats.items():
        n = sum(by_id[i]["ok"] for i in ids); o = sum(old_id[i]["ok"] for i in ids) if old else 0
        tot_n += n; tot_o += o
        L.append(f"| {cat} | {len(ids)} | " + (f"{o}/{len(ids)} | " if old else "") + f"{n}/{len(ids)} |")
    N = len(dataset["cases"])
    L.append(f"| **Total** | **{N}** | " + (f"**{tot_o}/{N}** | " if old else "") + f"**{tot_n}/{N}** |")
    L += ["", f"Temps moyen par réponse (recherche + règles, sans IA) : v2 = {sum(r['ms'] for r in new)/N:.1f} ms" + (f" ; v1 = {sum(r['ms'] for r in old)/N:.1f} ms." if old else "."), "",
          "## Détail par question", "", "| # | Catégorie | Question | " + ("v1 | " if old else "") + "v2 |", "|---|---|---|" + ("---|" if old else "") + "---|"]
    for c in dataset["cases"]:
        i = c["id"]
        L.append(f"| {i} | {c['category']} | {c['question']} | " + (("✅ | " if old_id[i]["ok"] else "❌ | ") if old else "") + ("✅ |" if by_id[i]["ok"] else "❌ |"))
    fails = [c for c in dataset["cases"] if not by_id[c["id"]]["ok"]]
    L += ["", "## Échecs restants en v2", ""]
    L += [f"- #{c['id']} « {c['question']} » : attendu {c['expect_all']} ; obtenu : {by_id[c['id']]['answer']}" for c in fails] or ["Aucun sur ce jeu de test."]
    L += ["", "## Limites", "",
          "- Les gains viennent surtout de : (1) l'ajout de la base de cours (v1 n'en avait pas), (2) la recherche multi-requêtes et bigrammes, (3) la prise en compte du contexte pour les questions de suivi, (4) les calculs déterministes. Ils ne prouvent rien sur la qualité des réponses générées par un modèle.",
          "- Les questions ont été écrites par le développeur après les corrections : le taux de réussite v2 est donc optimiste. Ajoutez vos propres questions réelles dans `tests/eval/dataset.json` et relancez le script.",
          "- Pour évaluer un vrai modèle : renseigner `LLM_API_KEY`, puis relire manuellement un échantillon de réponses (pertinence, exactitude, fidélité aux sources, langue)."]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"v2 : {tot_n}/{N}" + (f" | v1 : {tot_o}/{N}" if old else ""))


if __name__ == "__main__":
    main()
