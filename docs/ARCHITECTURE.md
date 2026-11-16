# Architecture v2

```
question ─► langue (lang.py)
          ─► salutations ─► calcul déterministe (calc.py) ─► règle « prix/frais » (aliases.py)
          ─► contexte : question de suivi ? (chat.contextualize)
          ─► recherche (retrieval.py) : BM25 + bigrammes, alias multilingues, filtre par base, multi-requêtes,
             pondération vérification, dédoublonnage, garde hors-sujet
          ─► rien trouvé ─► réponse fixe « non trouvé » + contacts (question enregistrée)
          ─► IA configurée ? oui : prompts.build_system (tuteur ou administratif + tâche + résumé) ─► llm.py (retries, secours étiqueté, tokens)
                              non : extrait brut de la base (MODE DÉMO, clairement indiqué)
```

- `db.py` : schéma SQLite, migration automatique avec **sauvegarde** (`nexa.db.bak-AAAAMMJJHHMMSS`).
- `knowledge.py` : bases intégrées (`onboarding` = JSON officiel v3, `cours` = `data/courses.md`) ; passages avec base, source, lieu, vérification, empreinte.
- `ingest.py` : adaptateurs par format → rapport d'ingestion → passages (`NEEDS_VERIFICATION`). Originaux conservés ; SQLite en lecture seule ; aucun SQL importé exécuté ; `.sql` refusé.
- `chunking.py` : découpage par titres, sans couper tableaux ni blocs de code.
- `__init__.py` : routes ; administration protégée (`ADMIN_PASSWORD`, sinon accès local uniquement ; en-tête `X-Requested-With` obligatoire sur les actions) ; journal sans contenu des questions.
- Isolation : chaque navigateur a un `client_id` ; une conversation n'est visible/ouvrable/supprimable que par son client.

## Ajouter une base sans toucher au code
Page **Bases de connaissances** → choisir le fichier et le nom de la base → « Importer et indexer ». Le rapport indique format, structure (tables, colonnes, clés, index pour SQLite), passages indexés, doublons ignorés. « Réindexer » relit le fichier original (détecte un changement de schéma) ; « Retirer » annule l'import (le fichier reste sur le disque).
