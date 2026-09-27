# Évaluation DevOps

Une petite API en Python (FastAPI) avec une base de données PostgreSQL.
Le projet montre un pipeline complet : Docker, tests automatiques, CI, CD, déploiement et métriques.

## Les routes de l'API

| Route | À quoi elle sert |
|---|---|
| `GET /health` | Dit si l'API et la base marchent (200 = OK, 503 = la base ne répond pas) |
| `POST /items` | Ajoute un item dans la base |
| `GET /items` | Affiche tous les items |
| `GET /metrics` | Affiche les chiffres pour Prometheus |

## Lancer le projet

Il faut avoir Git et Docker Desktop.

```bash
git clone https://github.com/souhilaachour/Evaluation-devops.git
cd Evaluation-devops
docker compose up -d --build
```

Ensuite, ouvrir http://localhost:8000/docs dans le navigateur.

Pour tout arrêter : `docker compose down`

## Lancer les tests

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
docker run -d --name pg-dev -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app -p 5432:5432 postgres:16.4-alpine
pytest -v
```

Les tests utilisent une vraie base PostgreSQL.
Ils vérifient que `/health` répond, qu'on peut ajouter puis lire un item, qu'un item vide est refusé et que `/metrics` marche.

## Docker

- L'image de base est fixée : `python:3.12.7-slim`.
- Le build se fait en 2 étapes (multi-stage) pour avoir une image plus légère.
- L'application ne tourne pas en root mais avec l'utilisateur `appuser`.
- Le `HEALTHCHECK` appelle `/health`, donc il vérifie aussi la base.
- Le `.dockerignore` enlève `.git`, `.venv` et les tests de l'image.
- Le `docker-compose.yml` lance 2 services : `api` et `db`. Le port 8000 est ouvert et chaque service a un healthcheck.

## La CI

Fichier : `.github/workflows/ci.yml`

Elle se lance à chaque pull request et à chaque push sur `main`. Elle a 4 jobs :

1. "lint" : vérifie le code Python avec `ruff` et les fichiers YAML avec `yamllint`.
2. "test" : lance les tests avec Python 3.11 et 3.12, avec une base PostgreSQL. Les rapports de tests sont sauvegardés.
3. "build" : vérifie que l'image Docker se construit.
4. "ci-ok" : devient rouge si un autre job a échoué. Il récupère aussi les rapports de tests.

Autres points :

- La branche `main` est protégée : on ne peut pas faire de merge si `ci-ok` est rouge.
- Le cache garde les bibliothèques Python entre deux runs. Le deuxième run va plus vite.
- Chaque job a une durée maximale (`timeout-minutes`).
- La CI a seulement le droit de lire le code (`permissions: contents: read`).

Action locale : `.github/actions/setup-python`.
Elle installe Python, active le cache et installe les bibliothèques.
La CI et la CD l'utilisent, pour ne pas répéter le même code.

## La CD

Fichier : `.github/workflows/cd.yml`

Elle se lance quand la CI est verte sur `main`. On peut aussi la lancer à la main avec le bouton **Run workflow** (choix `production`).

1. **build-push** : construit l'image et l'envoie sur le registry GitHub (`ghcr.io`) avec 3 tags :
   - `latest` : la dernière version
   - le SHA court du commit (ex : `a1b2c3d`)
   - une version `1.0.X`
2. **deploy** : se lance sur mon PC grâce à un runner GitHub installé dessus (self-hosted runner). Il :
   - note la version qui tourne en ce moment ;
   - télécharge et lance la nouvelle version ;
   - vérifie `/health` avec `curl`, en réessayant 3 fois ;
   - si ça ne marche pas, le job échoue et l'ancienne version est remise en place (rollback).

J'ai testé le rollback avec une version cassée exprès : l'API écoutait sur le mauvais port, le healthcheck a échoué et l'ancienne version a été remise en place.

## Les métriques

On les voit sur http://localhost:8000/metrics :

- `http_requests_total` : compte les requêtes, par route (`endpoint`) et par code HTTP (`code`).
- `http_request_duration_seconds` : mesure le temps de réponse de chaque route. Ça permet de calculer le p95 et le p99.
- `app_version_info` : montre quel commit est déployé.

## Les alertes

Fichier : `monitoring/alertes.yml`

**Trop d'erreurs 5xx** : plus de 5 % d'erreurs 5xx pendant 5 minutes.
- Pourquoi 5 % : normalement il n'y a presque jamais d'erreur 5xx, donc 5 % veut dire qu'il y a un vrai problème.
- Pourquoi 5 minutes : pour ne pas avoir d'alerte pour un petit pic, par exemple pendant un redémarrage.

**Latence trop haute** : le p95 dépasse 500 ms pendant 10 minutes.
- Pourquoi 500 ms : l'API répond normalement en quelques millisecondes, donc 500 ms c'est vraiment lent.
- Pourquoi 10 minutes : une lenteur est moins grave qu'une erreur, on attend plus longtemps pour éviter les fausses alertes.

Les règles ont été vérifiées avec l'outil `promtool`.

## Sécurité

- Le seul secret utilisé est le `GITHUB_TOKEN`. GitHub le crée tout seul à chaque run et le cache dans les logs.
- Ses droits sont limités avec le bloc `permissions`.
- Le mot de passe `postgres` visible dans les fichiers n'est pas un vrai secret : c'est une base locale pour les tests.
- Dans `yamllint`, j'ai désactivé les règles sur les fins de ligne, car je travaille sous Windows.

## Preuves

Toutes les étapes du projet sont expliquées avec des captures d'écran dans le document Word fourni avec le rendu : CI verte, cache HIT, protection de branche, CD, tags de l'image, métriques et test du rollback.