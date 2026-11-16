# Système de design MDO CHATBOT v2

Fichiers : `app/static/style.css` (tokens + composants), `app/templates/base.html` (mise en page, icônes SVG), `app/static/*.js`.

## Tokens
- Couleurs : Midnight `#0B1628`, Navy `#102A43`, Royal `#1D4E89`, Sky `#59B8F5`, Soft Blue `#EAF4FC` ; neutres `#F5F7FA / #FFFFFF / #E8EEF3 / #DCE4EC` ; texte `#172B4D / #64748B / #94A3B8` ; sémantiques `#16A34A / #D97706 / #DC2626 / #2563EB`.
- Thème clair et thème sombre conçus séparément (surfaces `#11233A`, bordures `#23405C`, accent bleu ciel), préférence mémorisée ; respect de `prefers-color-scheme` au premier lancement.
- Typographie : pile `Inter, Plus Jakarta Sans, Manrope, Segoe UI…` + polices arabes système (rendu RTL via `dir="auto"` dans le chat). Aucune police web externe n'est chargée (l'application fonctionne hors ligne) : si Inter est installée sur l'ordinateur, elle est utilisée, sinon Segoe UI / police système.
- Espacements 4–48 px, rayons 8/12/16 px, ombres légères, animations ≤ 200 ms, `prefers-reduced-motion` respecté.
- Composants : boutons (primary, accent, ghost, danger, icône), champs, cartes, badges, tableaux, boîtes de dialogue `<dialog>`, notifications (toasts), menus déroulants, indicateur de frappe.

## Navigation
Barre latérale repliable (mémorisée), groupes « Espace étudiant » / « Administration », conversations récentes (suppression), tiroir avec fond assombri sur mobile (Échap pour fermer).

## Chat
Rendu Markdown sûr (titres, listes, tableaux, code, liens http(s)/mailto uniquement ; aucun HTML interprété), zone de saisie multi-ligne (Entrée / Maj+Entrée), sélecteurs de source (Auto / Cours / Administratif) et de langue, actions : copier, régénérer, modifier la question, retour utile / à améliorer (enregistré), export Markdown. Chaque réponse indique : mode (IA + modèle / démo / règle / calcul), base utilisée, statut de vérification, sources.

## Pages
Tableau de bord (données réelles uniquement, états vides explicites), Assistant, Cours (19 modules), Modules & professeurs, Infos pratiques, Bases de connaissances (admin), Diagnostic (admin).

## Tests visuels réellement effectués
Chromium (Playwright), 4 configurations : bureau 1366×820 clair/sombre, mobile 390×800 clair/sombre ; 7 pages ; captures inspectées visuellement ; contrôle automatique : 0 erreur console, 0 débordement horizontal sur 27 vues ; tests de navigateur automatisés (`tests/test_frontend.py`) : rendu Markdown et protection XSS, envoi de message, retour persistant, thème et barre latérale mémorisés, tiroir mobile, import via l'interface.
Défauts trouvés puis corrigés pendant ces tests : boucle infinie du rendu Markdown (expression régulière partagée), italique `_…_` non rendu, colonne d'actions du tableau tronquée, débordement mobile de la page Diagnostic, listes déroulantes tronquées sur mobile.
Non testé : Firefox / Safari, lecteurs d'écran, rendu avec la police Inter installée.
