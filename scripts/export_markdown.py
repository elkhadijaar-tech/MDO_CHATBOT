"""Exporte la base en Markdown (utile pour l'importer comme base de connaissances dans Botpress)."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
kb = json.loads((root / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
out = ["# " + kb["title"], ""]
for s in kb["sections"]:
    out += ["## " + s["title"], ""] + ["- " + i for i in s["items"]] + [""]
out += ["## Questions fréquentes", ""]
for f in kb["faq"]:
    out += [f"**{f['q']}**", f["a"], ""]
out += ["## Programme des modules et professeurs - filière MDO", ""]
for sem in (1, 2, 3, 4):
    out += [f"### Semestre {sem}", ""]
    out += [f"- {n} : {p or 'professeur non indiqué dans la base'}" for s_, n, p in kb["modules"] if s_ == sem] + [""]
target = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "docs" / "base_de_connaissances.md"
target.write_text("\n".join(out), encoding="utf-8")
print("Écrit :", target)
