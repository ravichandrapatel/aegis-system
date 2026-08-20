# Zone 1 — Inbox

Drop raw notes, logs, dumps, or drafts here.

- Treat inbox files as **immutable** until ingested.
- Ask OKF to **MAINTAIN / INGEST** using [vault/playbooks/maintain-okf-system.md](../vault/playbooks/maintain-okf-system.md).
- After a successful ingest/archive, **empty the active inbox**: move the source to [`_archive/`](_archive/) (or delete it). Leave only this README and `.gitkeep`.

Do not put secrets in a shared zip of this package.
