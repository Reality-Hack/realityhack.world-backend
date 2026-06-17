# Agent instructions — realityhack.world-backend

## Python environment

Use **uv**, not Poetry, for dependency management and running Python commands in this repo.

Poetry metadata in `pyproject.toml` / `poetry.lock` is legacy. Install from `requirements.txt` (compiled from `pyproject.toml`).

### Prerequisites

- Python 3.10 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) installed

### Setup

```bash
cd realityhack.world-backend
uv venv
uv pip install -r requirements.txt
```

`uv` creates `.venv/` in the project root by default.

### Running commands

Prefix Django and other Python entrypoints with `uv run` so they use the project virtualenv:

```bash
uv run python manage.py migrate
uv run python manage.py test
uv run python manage.py test infrastructure.tests.RsvpQuestionMigrationTests
uv run python manage.py migrate_rsvp_to_dynamic_questions --dry-run
uv run python manage.py spectacular --file schema.yml
```

Or use the existing shell scripts after syncing deps:

```bash
uv pip install -r requirements.txt
./test
```

### Environment variables

Copy and configure env before running locally:

```bash
cp .env.example .env
```

Load `.env` / `.env.local` as needed for Keycloak, database, etc.

For tests without a full `.env`, minimal exports (see `.woodpecker.yml`):

```bash
export DJANGO_SECRET_KEY=test DEBUG=true DEPLOYED=false
export FRONTEND_DOMAIN=http://localhost:3000 BACKEND_DOMAIN=http://localhost:8000
export KEYCLOAK_SERVER_URL=https://dev-api.realityhack.world:8443/
export KEYCLOAK_REALM=master KEYCLOAK_CLIENT_ID=123456 KEYCLOAK_CLIENT_SECRET_KEY=123456
export EMAIL_HOST=smtp.gmail.com EMAIL_PORT=465 EMAIL_USE_SSL=True
export EMAIL_HOST_USER= EMAIL_HOST_PASSWORD=
```

### Do not use

- `poetry install` / `poetry run` — use `uv` instead
- `pip install` outside the uv-managed `.venv` unless explicitly required

### Updating dependencies

When changing `pyproject.toml`, recompile lockfile and sync:

```bash
uv pip compile pyproject.toml -o requirements.txt
uv pip install -r requirements.txt
```
