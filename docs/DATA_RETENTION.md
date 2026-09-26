# Data Retention & Cleanup Policies

## 1. Local Storage Directory Map
```text
data/
├─ db/
│  └─ studio.sqlite          # SQLite WAL database
├─ sources/                  # Downloaded raw source media & articles
├─ projects/                 # Project workspace assets & scratch files
├─ assets/                   # Shared image/video/audio assets
├─ voice/                    # Generated TTS audio clips
├─ subtitles/                # Aligned subtitle files (.srt, .vtt, .json)
├─ renders/                  # Intermediate & final video renders
├─ exports/                  # Final export packages
├─ cache/                    # Ephemeral HTTP / parsed cache
├─ tmp/                      # Worker temp scratch files
└─ backups/                  # SQLite & configuration snapshots
```

## 2. Retention Periods & Thresholds
| Category | Default TTL | Deletion Condition |
|---|---|---|
| `tmp/` scratch files | 24 hours | Age > 24h, automatic |
| `cache/` entries | 24 hours | Expired or manual refresh |
| Failed render temps | 3 days | Render job status == FAILED |
| Downloaded source media | 7 days | No active project reference |
| Unused generated assets | 7 days | Not attached to any project scene |
| Final renders | 30 days | All platform publications verified |
| Export packages | 30 days | Default retention; can be archived |
| SQLite database metadata | Indefinite | Never automatically deleted |
| Analytics & Research Citations | Indefinite | Retained for historical learning |

## 3. Reference-Safe Deletion Rules
Files must **never** be deleted if:
1. Referenced by an active project (`status != ARCHIVED`).
2. Required by a pending or active render job.
3. Referenced by an export package marked `READY_TO_PUBLISH` or `PARTIALLY_PUBLISHED`.
4. Any platform publication state remains `READY`.

The `CleanupEngine` strictly supports dry-run preview, bytes-recoverable calculation, and idempotent execution with complete audit logging.
