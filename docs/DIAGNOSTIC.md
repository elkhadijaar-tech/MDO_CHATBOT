# Diagnostic technique de MDO CHATBOT v1 (avant mise à niveau)

Méthode : lecture du code de la v1 + exécution du jeu de test `tests/eval/dataset.json` sur la v1 (voir `BENCHMARK.md`).
Les causes ci-dessous sont **observées dans le code ou mesurées** ; les effets sur la qualité d'un vrai modèle d'IA ne
peuvent pas être mesurés sans clé API et sont signalés comme hypothèses.

| # | Cause racine constatée | Preuve | Correctif v2 |
|---|---|---|---|
| 1 | **Une seule base (101 passages administratifs), aucun contenu de cours** | v1 : 0/14 questions de cours (`not_found`) | Base « cours » (19 modules, 56 passages) + système multi-bases |
| 2 | **L'historique n'était jamais utilisé pour la recherche** : « Et pour la SA ? » cherchait la phrase seule | v1 : 0/4 questions de suivi | `contextualize()` + repli « question seule puis question précédente » |
| 3 | **Prompt unique et strict, pensé pour l'administratif** (« uniquement avec le contexte », « réponses courtes ») : inadapté à l'explication de cours (hypothèse sur l'effet réel) | `messages.SYSTEM_PROMPT` | Prompts modulaires `prompts.py` : tuteur (cours) / administratif, conseils par tâche (QCM, résumé, plan, comparaison, exemple, calcul), langue, résumé de conversation |
| 4 | **Contexte rudimentaire** : 6 derniers messages, aucune limite en tokens, aucun résumé | `chat._messages` | `trim_history` (budget) + résumé extractif des anciennes questions ; contexte numéroté [1], [2]… |
| 5 | **Recherche à un seul passage de requête**, mots isolés uniquement : les questions composées perdaient une moitié | v1 : 0/2 questions composées | Multi-requêtes, bigrammes, métadonnées (base, vérification), dédoublonnage |
| 6 | **Aucun calcul fiable** : le calcul était laissé au modèle | v1 : 0/5 | `calc.py` : TVA, intérêts simples/composés, escompte, avec étapes (jamais de devinette si donnée manquante) |
| 7 | **Aucune observabilité** : pas d'identifiant de requête, pas de durée, pas de tokens, pas de test de connexion | code | Journal `data/logs/nexa.log`, `X-Request-ID`, tokens, page Diagnostic, test réel de connexion |
| 8 | **Fournisseur LLM unique, sans modèle de secours étiqueté** | `llm.py` | anthropic / openai / gemini / compatible OpenAI ; secours optionnel **toujours signalé** dans la réponse |
| 9 | **Base figée** : ajouter des données imposait de modifier le code | code | Import dynamique (PDF, DOCX, PPTX, XLSX, CSV, JSON, TXT, MD, SQLite), rapport d'ingestion, réindexation, retrait |
| 10 | **Risque de hors-sujet** une fois la base élargie (ex. « capitale de la France » trouvait « capitale » dans le cours d'institutions) | test unitaire | Garde de couverture lexicale du meilleur passage |

## Ce qui n'a PAS été traité (honnêteté)
- Recherche web : non implémentée (pas d'accès réseau dans l'environnement de développement).
- Recherche sémantique par embeddings et reranking par modèle : non implémentés (BM25 + bigrammes ; aucun modèle d'embedding requis).
- Réponses en streaming : non implémentées (indicateur de frappe uniquement).
- Appels réels à un modèle : non testés (simulés dans les tests).
