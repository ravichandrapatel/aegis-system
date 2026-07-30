# Zone 1 — Inbox

Drop raw notes, logs, dumps, or drafts here.

- Treat inbox files as **immutable** until ingested.
- Ask Aegis to **MAINTAIN / INGEST** using [vault/playbooks/maintain-aegis-system.md](../vault/playbooks/maintain-aegis-system.md).
- After a successful ingest/archive, **empty the active inbox**: move the source to [`_archive/`](_archive/) (or delete it). Leave only this README and `.gitkeep`.

Do not put secrets in a shared zip of this package.
