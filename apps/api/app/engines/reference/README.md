# Reference Benchmark Engine (`reference`)

The **Reference Benchmark Engine** serves as the canonical architectural exemplar for all 13 feature engines in the Fresh Local AI Content Studio.

## Purpose
Demonstrates full contract adherence:
1. Manifest-driven configuration (`manifest.yaml`)
2. Typed contracts (`contracts.py`)
3. Versioned rules (`rules.yaml`)
4. Active health checking (`health()`)
5. Dry-run execution (`dry_run()`)
6. Production execution (`run()`)
7. Result explainability (`explain()`)
8. Isolated test suite (`tests/`)

## Contracts
- **Input:** `BenchmarkSignal` (id, title, metric_value, category)
- **Output:** `BenchmarkReport` (id, status, score, passed, reason)
