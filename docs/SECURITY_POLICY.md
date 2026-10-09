# Politique de sécurité — CycloPass API

## Signaler une vulnérabilité

**Ne publiez pas la faille dans une issue publique.** Utilisez l'un de ces deux canaux privés :

1. **GitHub** : onglet *Security* du dépôt → **Report a vulnerability** (signalement privé, visible seulement par l'équipe).
2. **E-mail** : `security@cyclopass.example`

Merci d'indiquer :

- la route ou le composant concerné et la version (`/health`, fichier `VERSION` ou tag d'image) ;
- les étapes pour reproduire, avec la requête exacte si possible ;
- l'impact que vous avez constaté (données lues, modifiées, service interrompu) ;
- vos coordonnées si vous souhaitez être crédité.

Les tests de bonne foi qui respectent cette politique ne feront l'objet d'aucune poursuite : pas d'accès aux données d'autres usagers au-delà de la preuve minimale, pas de déni de service, pas d'ingénierie sociale contre les équipes.

## Versions couvertes

| Version | Couverte |
|---|---|
| Dernière version déployée en production (`cyclopass-deploy`) | ✅ |
| Version précédente (cible de rollback) | ✅ correctifs critiques uniquement |
| Code legacy de 2019 | ❌ retiré, ne doit plus tourner nulle part |

## Délais de traitement selon la criticité

La criticité est évaluée par le **Security Champion** avec le score CVSS v3.1, puis ajustée au contexte CycloPass (exposition sur Internet, données d'usagers, ouverture aux partenaires).

| Criticité | CVSS | Exemple chez CycloPass | Accusé de réception | Contournement en prod | Correctif déployé |
|---|---|---|---|---|---|
| 🔴 **Critique** | 9.0 – 10 | Injection SQL, exécution de code à distance, secret de prod exposé | **24 h** | **24 h** (désactiver la route, révoquer le secret) | **72 h** |
| 🟠 **Haute** | 7.0 – 8.9 | Contournement de la clé d'API, dépendance avec exploit public | 48 h | 72 h si possible | **7 jours** |
| 🟡 **Moyenne** | 4.0 – 6.9 | Fuite d'information dans une erreur, absence de rate limiting | 5 jours ouvrés | — | **30 jours** |
| 🟢 **Faible** | 0.1 – 3.9 | En-tête de sécurité manquant | 5 jours ouvrés | — | **90 jours** ou prochain sprint |

Les mêmes délais s'appliquent aux **vulnérabilités de dépendances** remontées par `pip-audit`, Dependabot ou Trivy.

## Déroulement

1. **Réception** : le Security Champion accuse réception dans le délai et ouvre un *security advisory* privé sur GitHub.
2. **Qualification** : il reproduit la faille, fixe la criticité et désigne un développeur.
3. **Contournement** (critique / haute) : mesure immédiate, par exemple désactiver la route, révoquer et régénérer un secret, ou faire un rollback via `cyclopass-deploy`.
4. **Correctif** : branche privée, test de non-régression qui reproduit la faille, revue par une deuxième personne, passage complet du pipeline (aucune dérogation sur le contrôle qui concerne la faille).
5. **Déploiement** : nouvelle version, puis commit du nouveau tag dans `cyclopass-deploy`.
6. **Communication** : réponse au rapporteur, publication de l'advisory après correction, et information des partenaires si leurs intégrations sont concernées.
7. **Retour d'expérience** sous 5 jours pour les failles critiques et hautes : cause racine, et contrôle à ajouter au pipeline pour que ça ne se reproduise pas.

## Divulgation

Nous appliquons une **divulgation coordonnée** : le rapporteur s'engage à ne rien publier avant le correctif, ou au plus tard **90 jours** après son signalement. Le délai peut être prolongé d'un commun accord.

## Secrets exposés

Tout secret qui a été visible hors de son coffre est considéré comme **compromis**, même s'il a été retiré du code depuis :

1. **Révoquer et régénérer** immédiatement le secret chez son fournisseur.
2. Mettre la nouvelle valeur dans le gestionnaire de secrets (GitHub Secrets, variables d'environnement du déploiement), jamais dans le code.
3. Vérifier dans les journaux du fournisseur si le secret a été utilisé.
4. Nettoyer l'historique Git si nécessaire. Cela ne dispense jamais de l'étape 1.
