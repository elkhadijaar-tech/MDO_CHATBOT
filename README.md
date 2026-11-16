# MDO CHATBOT v2 — Assistant et tuteur MDO · EST Casablanca

Chatbot pour les étudiants de **1re année MDO** (ESTC Casablanca) :
- **Intégration** : absences, certificat médical, rattrapage, modules et professeurs (S1–S4), démarches, formations, vie étudiante (base officielle v3) ;
- **Cours** : référentiel de 19 modules (comptabilité, droit, marketing, statistiques, SQL, Excel…) avec explications, formules et **calculs pas à pas** (TVA, intérêts simples/composés, escompte) ;
- **Bases extensibles** : importez de nouveaux documents ou bases de données depuis l'interface, sans modifier le code.

Langues : français, anglais, arabe, darija (détection automatique ou choix manuel).

## Installation (Windows, pour débutant)
1. Installez **Python 3.10 ou plus** : <https://www.python.org/downloads/> (cochez **« Add python.exe to PATH »**).
2. Clic droit sur le ZIP > **Extraire tout**.
3. **Double-cliquez sur `run.bat`**, attendez l'installation automatique (Internet requis la 1re fois).
4. Le navigateur s'ouvre sur **http://127.0.0.1:5000**. Linux/macOS : `./run.sh`.

**Si vous aviez la v1** : copiez votre ancien dossier `data/nexa.db` dans le nouveau avant de lancer ; la base est migrée automatiquement et une sauvegarde `nexa.db.bak-…` est créée.

## Mode DÉMO ou mode IA
- **Sans clé API** : MODE DÉMO, clairement affiché. Les réponses sont des extraits de la base (pas de l'IA). Les calculs et règles fonctionnent. Les résumés, QCM et plans de révision demandent l'IA.
- **Avec une clé API** : éditez `.env` (créé au premier lancement) :
  ```
  LLM_PROVIDER=anthropic   (ou openai, gemini, openai-compatible)
  LLM_API_KEY=votre_cle
  LLM_MODEL=claude-sonnet-5-5
  LLM_FALLBACK_MODEL=       (optionnel : toujours signalé dans la réponse)
  ```
  Puis ouvrez **Diagnostic → Tester la connexion IA** : la connexion n'est déclarée « vérifiée » qu'après ce test réel.
- Ne partagez jamais `.env`.

## Administration
Pages **Bases de connaissances** et **Diagnostic** : accessibles depuis l'ordinateur qui héberge l'application, ou avec un mot de passe (`ADMIN_PASSWORD` dans `.env`) si vous exposez l'application sur un réseau.
Import : PDF, DOCX, PPTX, XLSX, CSV, JSON, TXT, MD, SQLite (.sqlite/.db). Le contenu importé est marqué « à vérifier ». Les dumps `.sql` sont refusés (sécurité).

## Ce qui a été testé / ce qui ne l'a pas été
- **Testé** (68 tests automatiques, dont 4 en vrai navigateur Chromium) : recherche, règles, calculs, contexte, import des 9 formats, administration, isolation des conversations, migration, rendu Markdown sécurisé, thèmes, mobile. Benchmark : `docs/BENCHMARK.md` (v1 : 19/46 → v2 : 46/46 sur le jeu de test ; limites expliquées dans le fichier).
- **Non testé** : appels réels à un fournisseur d'IA (simulés), `run.bat` sous Windows, Firefox/Safari, lecteurs d'écran.
- **Non implémenté** : recherche web, recherche par embeddings, streaming, OCR, pages « Recherche / Écriture / Code / Bibliothèque de prompts », pièces jointes dans le chat. La qualité réelle des réponses de l'IA dépend du modèle choisi et n'a pas été mesurée.

## Documentation
`docs/DIAGNOSTIC.md` (causes des faiblesses de la v1), `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/BENCHMARK.md`.
Tests : `python -m pytest -q` ou `python -m unittest discover -s tests -t .` · Évaluation : `python scripts/run_eval.py --baseline CHEMIN_V1`.

## Points de la base à faire confirmer
Professeur de « Institutions administratives et politiques (Arabe) » (S1) non indiqué ; orthographe Outski (S3) / Outseki (S4) ; prénoms manquants ; nom du Chef de Filière MDO non indiqué. Le référentiel de cours est repris tel que fourni : à valider avec les enseignants (ex. règles juridiques et barèmes).
