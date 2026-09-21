# AegisLocal MVP deployment runbook

This runbook starts the FastAPI API with Redis-backed transient state and
SQLite audit persistence. It does not deploy the frontend, a reverse proxy, or
the future PostgreSQL/ML services.

## Prerequisites

- Docker Engine 24+ and the Docker Compose plugin
- A free local port (8000 by default)

## Start the stack

From the repository root:

```bash
cp infra/docker/.env.example infra/docker/.env
# Replace REDIS_PASSWORD with a unique value.
docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml up -d --build
```

PowerShell equivalent:

```powershell
Copy-Item infra/docker/.env.example infra/docker/.env
# Edit infra/docker/.env and replace REDIS_PASSWORD.
docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml up -d --build
```

The API is intentionally bound to `127.0.0.1`; put it behind an authenticated
TLS reverse proxy before exposing it to a network. Redis has no host port
mapping and is reachable only by the Compose network.

## Verify and operate

```bash
curl http://127.0.0.1:8000/health
docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml ps
docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml logs -f api
```

Prometheus and Grafana are optional local operators:

```bash
docker compose --env-file infra/docker/.env \
  -f infra/docker/docker-compose.yml --profile ops up -d
```

They are not exposed securely by default; keep this profile on a trusted
machine or add authentication and a TLS proxy.

## Persistence and shutdown

- `aegis_data` stores `/data/audit.sqlite3` (derived decision evidence).
- `redis_data` stores Redis AOF data (rate-limit keys and challenges).
- Raw trajectories are not written to the audit database.

Stop without deleting data:

```bash
docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml down
```

Delete the stack and all persisted data only when intentionally resetting the
environment:

```bash
docker compose --env-file infra/docker/.env \
  -f infra/docker/docker-compose.yml down -v
```

## Configuration

For a non-container local run, copy `backend/.env.example` to `backend/.env`.
For Compose, use `infra/docker/.env`; the Compose file supplies the container
settings and mounts the audit data volume at `/data`. Never commit either
`.env` file or a real Redis password.
