# Architecture Overview — Fresh Local AI Content Studio

## 1. System Topology

```mermaid
flowchart TB
    subgraph UI_Layer ["Frontend Application (apps/web)"]
        NextUI["Next.js App Router (localhost:3000)"]
        Pages["/ (Dashboard)\n/opportunities\n/projects\n/engines\n/settings"]
        Launcher["Platform Launcher Module"]
        NextUI --> Pages
        NextUI --> Launcher
    end

    subgraph API_Layer ["Backend API (apps/api)"]
        FastAPIApp["FastAPI Server (localhost:8000)"]
        Endpoints["/health\n/api/v1/niche\n/api/v1/brand\n/api/v1/engines\n/api/v1/projects"]
        Registry["Engine Registry"]
        FastAPIApp --> Endpoints
        FastAPIApp --> Registry
    end

    subgraph Engine_Layer ["13 Independent Feature Engines"]
        Engines["RSS Engine\nTrends Engine\nNiche Guard\nOpportunity Scoring\nBrand Engine\nResearch Engine\nOriginality Engine\nAI Provider\nContent Engine\nMedia Engine\nExport Engine\nAnalytics Engine\nCleanup Engine"]
        Registry --> Engines
    end

    subgraph Worker_Layer ["Background Worker (worker/)"]
        PythonWorker["worker.py (Async Process)"]
        Jobs["FFmpeg Render Queue\nTTS Generation\nSubtitle Alignment\nHeavy Batch Fetches"]
        PythonWorker --> Jobs
    end

    subgraph Data_Layer ["Storage & Database (data/)"]
        SQLiteDB[("SQLite WAL Database\nstudio.sqlite")]
        MediaDir["Local Filesystem\nassets/ voice/ renders/ exports/"]
    end

    UI_Layer -->|HTTP REST / JSON| API_Layer
    API_Layer -->|Async SQLAlchemy / WAL| SQLiteDB
    Worker_Layer -->|Poll Jobs / Write Status| SQLiteDB
    Worker_Layer -->|Produce Media| MediaDir
    Launcher -.->|target='_blank' HTTPS| Browser["Default Web Browser\n(YouTube / Meta / TikTok)"]
```

## 2. Core Architectural Principles
1. **Engine Independence:** Engines communicate only through typed inputs and outputs defined in `contracts.py`. Modifying an internal engine implementation (e.g., swapping RSS parsers or adjusting trend weights) has zero side effects on unrelated engines.
2. **Local-First Reliability:** Single-user operation runs without Docker, external Postgres, or Redis daemons. SQLite WAL mode provides high-concurrency read access during background worker processing.
3. **Decoupled Heavy Processing:** HTTP request handlers never execute blocking FFmpeg renders or long batch scrapes. Jobs are enqueued in SQLite and executed by `worker.py`.
4. **Auditability & Explainability:** Every engine execution records input counts, output counts, rejected items, latency, cost, and human-readable explanation logs.
