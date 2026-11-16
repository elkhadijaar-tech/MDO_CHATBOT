# Benchmark MDO CHATBOT

Jeu de test : `tests/eval/dataset.json` (46 questions). Généré par `scripts/run_eval.py` le 2026-11-15.

**Ce que mesure ce benchmark :** l'infrastructure (recherche, règles de sécurité, calculs, prise en compte du contexte), exécutée **sans clé API** (mode démo). Un test est réussi si tous les extraits attendus figurent dans la réponse. **Il ne mesure pas la qualité rédactionnelle d'un modèle d'IA** : aucun score de ce type n'est annoncé, car aucun appel réel à un modèle n'a été fait.

| Catégorie | Questions | v1 (avant) | v2 (après) |
|---|---|---|---|
| onboarding | 10 | 10/10 | 10/10 |
| multilingue | 6 | 5/6 | 6/6 |
| cours | 14 | 0/14 | 14/14 |
| calcul | 5 | 0/5 | 5/5 |
| suivi | 4 | 0/4 | 4/4 |
| question composée | 2 | 0/2 | 2/2 |
| sécurité/hors base | 5 | 4/5 | 5/5 |
| **Total** | **46** | **19/46** | **46/46** |

Temps moyen par réponse (recherche + règles, sans IA) : v2 = 1.6 ms ; v1 = 0.8 ms.

## Détail par question

| # | Catégorie | Question | v1 | v2 |
|---|---|---|---|---|
| 1 | onboarding | Où déposer mon certificat médical ? | ✅ | ✅ |
| 2 | onboarding | Que se passe-t-il si je dépasse 50% d'absences ? | ✅ | ✅ |
| 3 | onboarding | Quelle est la note maximale au rattrapage ? | ✅ | ✅ |
| 4 | onboarding | Quels sont les horaires de l'administration ? | ✅ | ✅ |
| 5 | onboarding | Où demander une attestation de scolarité ? | ✅ | ✅ |
| 6 | onboarding | Qui enseigne Business English ? | ✅ | ✅ |
| 7 | onboarding | Quels sont les modules du S2 ? | ✅ | ✅ |
| 8 | onboarding | Qui est le professeur de Institutions administratives ? | ✅ | ✅ |
| 9 | onboarding | Quel département contient MDO ? | ✅ | ✅ |
| 10 | onboarding | Où voir l'emploi du temps ? | ✅ | ✅ |
| 11 | multilingue | Where can I submit my medical certificate? | ✅ | ✅ |
| 12 | multilingue | What happens if I exceed 50% absences? | ✅ | ✅ |
| 13 | multilingue | كيفاش نقدم الشهادة الطبية | ✅ | ✅ |
| 14 | multilingue | ما هي ساعات عمل الإدارة؟ | ❌ | ✅ |
| 15 | multilingue | فين كاينة المدرسة | ✅ | ✅ |
| 16 | multilingue | شنو هي النقطة القصوى فالاستدراك | ✅ | ✅ |
| 17 | cours | Qu'est-ce que la SARL ? | ❌ | ✅ |
| 18 | cours | Quelle est la formule de la variance ? | ❌ | ✅ |
| 19 | cours | Quelle est la période d'essai pour un cadre ? | ❌ | ✅ |
| 20 | cours | Comment faire un amortissement dégressif ? | ❌ | ✅ |
| 21 | cours | Quelle est la formule de la loi binomiale ? | ❌ | ✅ |
| 22 | cours | Quelles sont les étapes de l'entretien de vente ? | ❌ | ✅ |
| 23 | cours | What is the PODC process? | ❌ | ✅ |
| 24 | cours | Quels sont les éléments constitutifs de l'État ? | ❌ | ✅ |
| 25 | cours | Quelle est la différence entre SA et SARL ? | ❌ | ✅ |
| 26 | cours | Explique la partie double | ❌ | ✅ |
| 27 | cours | Quelle est la formule du coût marginal ? | ❌ | ✅ |
| 28 | cours | À quoi sert la matrice SWOT ? | ❌ | ✅ |
| 29 | cours | Qu'est-ce qu'une jointure SQL ? | ❌ | ✅ |
| 30 | cours | Quelle est la durée légale du travail au Maroc ? | ❌ | ✅ |
| 31 | calcul | Calcule la TVA à 20% sur 1000 DH HT | ❌ | ✅ |
| 32 | calcul | Un produit coûte 600 DH TTC avec une TVA de 20%, quel est le prix HT ? | ❌ | ✅ |
| 33 | calcul | Intérêts composés : capital 10000 DH, taux 5%, pendant 3 ans | ❌ | ✅ |
| 34 | calcul | Intérêts simples : 5000 DH à 6% pendant 9 mois | ❌ | ✅ |
| 35 | calcul | Escompte commercial d'un effet de 12000 DH à 8% pendant 45 jours | ❌ | ✅ |
| 36 | suivi | Et pour la SA ? | ❌ | ✅ |
| 37 | suivi | Et l'écart-type ? | ❌ | ✅ |
| 38 | suivi | Dans quel délai ? | ❌ | ✅ |
| 39 | suivi | Donne un exemple | ❌ | ✅ |
| 40 | question composée | Qu'est-ce que la SARL et comment calculer la TVA ? | ❌ | ✅ |
| 41 | question composée | Quelle est la règle pour les absences et les horaires de l'administration ? | ❌ | ✅ |
| 42 | sécurité/hors base | Quel est le prix de l'inscription ? | ✅ | ✅ |
| 43 | sécurité/hors base | Combien coûte l'ESTC ? | ✅ | ✅ |
| 44 | sécurité/hors base | recette du couscous | ✅ | ✅ |
| 45 | sécurité/hors base | Quelle est la capitale de la France ? | ✅ | ✅ |
| 46 | sécurité/hors base | Qui est le président des États-Unis ? | ❌ | ✅ |

## Échecs restants en v2

Aucun sur ce jeu de test.

## Limites

- Les gains viennent surtout de : (1) l'ajout de la base de cours (v1 n'en avait pas), (2) la recherche multi-requêtes et bigrammes, (3) la prise en compte du contexte pour les questions de suivi, (4) les calculs déterministes. Ils ne prouvent rien sur la qualité des réponses générées par un modèle.
- Les questions ont été écrites par le développeur après les corrections : le taux de réussite v2 est donc optimiste. Ajoutez vos propres questions réelles dans `tests/eval/dataset.json` et relancez le script.
- Pour évaluer un vrai modèle : renseigner `LLM_API_KEY`, puis relire manuellement un échantillon de réponses (pertinence, exactitude, fidélité aux sources, langue).
