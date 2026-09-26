# Architecture Decision Records (ADR Log)

## ADR-001: SQLite with WAL Mode as Initial Local Database
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** Single-user local desktop environment requiring zero-friction installation without external database services.
- **Decision:** Utilize SQLite 3 with Write-Ahead Logging (`journal_mode=WAL`) via `aiosqlite` and `SQLAlchemy 2.0`.
- **Consequences:** Near-instant boot, zero host daemons, concurrent non-blocking reads during worker write jobs. Repositories must maintain clean SQL abstraction for seamless future PostgreSQL migration if multi-user support is ever required.

## ADR-002: Independent Background Worker Process
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** Long-running operations such as media rendering, FFmpeg encoding, TTS synthesis, and batch RSS discovery would block HTTP threads and lead to UI timeouts.
- **Decision:** Scaffold a dedicated `worker/worker.py` daemon that polls SQLite-backed job tables.
- **Consequences:** Robust execution isolation. Worker restarts or crashes do not bring down the FastAPI server or UI.

## ADR-003: Browser Launcher for V1 Platform Publishing
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** Social media platform direct APIs (YouTube Data API, Meta Graph API, TikTok Direct Post) require complex enterprise verification, OAuth app approvals, token refreshes, and introduce high fragility.
- **Decision:** Provide native one-click browser launcher buttons (`target="_blank"`, `rel="noopener noreferrer"`) opening authenticated upload pages in the user's everyday browser, paired with one-click clipboard copying of title, description, captions, and hashtags.
- **Consequences:** Zero API approval friction, 100% compliance with platform terms, zero security exposure of user platform tokens.

## ADR-004: Engine Isolation & Contract-Driven Design
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** AI and content tools frequently degrade when coupled into massive monolithic scripts or fragile pipeline graphs.
- **Decision:** Enforce 13 decoupled engines with typed Pydantic contracts, standalone manifests, independent rules, logs, and explainability.
- **Consequences:** Any engine can be upgraded, mocked, or refactored independently without regression to other studio features.
