# PayeTonKawa – API Clients

Micro-service de inscription, connexion (émission des jetons JWT) et gestion des fiches clients. Django 5.2 + Django REST Framework, base PostgreSQL dédiée (SQLite en développement).

## Lancer seul (développement)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8001
```

Documentation interactive : http://localhost:8001/api/docs/ (via la passerelle : http://localhost:8080/client/api/docs/)

La plateforme complète (3 services, RabbitMQ, PostgreSQL, passerelle, supervision) se lance depuis le dépôt **payetonkawa-infra**.

## Endpoints

| Méthode | URL | Accès |
|---|---|---|
| POST | `/api/auth/register/` | public |
| POST | `/api/auth/login/` · `/api/auth/refresh/` | public |
| GET, POST | `/api/clients/` (`?search=`, `?type_client=`, `?ordering=`) | admin |
| GET, PUT, PATCH, DELETE | `/api/clients/{id}/` | admin ou le client lui-même |
| GET | `/api/clients/me/` | client connecté |

Authentification : en-tête `Authorization: Bearer <jeton>` (jeton obtenu sur le service Clients).

## Événements RabbitMQ

Publie `client.created`, `client.updated`, `client.deleted`.

## Tests

```bash
python manage.py test                       # tests unitaires et d'intégration
coverage run manage.py test && coverage report
flake8 .
```

## Commandes utiles

`python manage.py import_crm` : reprise des clients de l'ancien CRM.

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` | sécurité Django |
| `JWT_SIGNING_KEY` | clé partagée de signature des jetons |
| `DB_ENGINE=postgres`, `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | base de données |
| `RABBITMQ_ENABLED`, `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` | message broker |
| `URL_PREFIX` | préfixe derrière la passerelle (`/client`) |
