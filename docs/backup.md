# Backups

## Scope

Included:

- Postgres databases (`ateam`, and optional profile databases)
- Named Docker volume `postgres-data`
- Files under `config/`, `skills/`, and `prompts/`

Not included:

- Secrets (`.env`, wizard secret store). Keep those in your secret store and rotate them.

## Schedule

Default: nightly, keep 7 dailies. Adjust on the host (cron or your backup tool).

## Commands

```bash
make backup       # writes backups/ateam-latest.sql
make restore      # loads backups/ateam-latest.sql into Postgres
make clean        # stops containers; keeps the postgres-data volume
make purge-logs   # TRUNCATE spend_events, email_sink (stack must be up)
make reset-data   # docker compose down -v after a yes prompt; deletes postgres-data
# CONFIRM=yes make reset-data   # skip the prompt (scripts only)
```

Restore test: `make backup && make down && make up && make restore`, then confirm the seeded `welcome` demo record is present.

Last restore-test date: 2026-10-14 (package self-check on the stub stack).
