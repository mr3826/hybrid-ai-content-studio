# Testing Strategy & Guidelines

## 1. Testing Philosophy
The studio enforces rigorous multi-layered testing across backend API, feature engines, worker processes, and the Next.js web application.

## 2. Test Tiers

### A. Backend Unit & API Tests (`pytest`)
- Located in `apps/api/tests/`.
- Tests endpoints, database transactions, engine registry, and repository layers.
- Uses in-memory or temporary SQLite database fixtures.
- Command:
  ```bash
  pytest apps/api/tests/ -v
  ```

### B. Engine Isolation Tests
- Located within each engine's `tests/` directory (e.g., `apps/api/app/engines/rss/tests/`).
- Validates that engine inputs/outputs adhere strictly to `contracts.py`.
- Tests failure isolation (e.g., corrupt RSS feed does not throw unhandled exceptions).
- Tests mock provider fallbacks without making live network calls.

### C. Frontend Unit & Type Checks
- Next.js TypeScript validation and React component unit testing.
- Command:
  ```bash
  npm --prefix apps/web run build
  ```

### D. End-to-End Verification (Playwright)
- Validates critical user journeys:
  - First-run single niche/brand setup
  - Refreshing RSS candidates
  - Approving opportunities for research
  - Script block editing and regeneration
  - Platform launcher one-click copy and link targets

## 3. Mandatory CI/CD Prohibition
All tests are run locally. No GitHub Actions or cloud CI/CD pipelines are created.
