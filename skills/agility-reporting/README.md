# Agility Reporting Skill (source not yet in repo)

The reporting skill content (SKILL.md + references, 14 chunks) currently lives at:

```
C:\Users\indha\OneDrive - Beisser Lumber\ai\skills\agility-reporting\
```

and is ingested with `pi_backend/scripts/ingest_reporting_skill.py`, which reads
from that OneDrive path by default.

## Migrating it into the repo (recommended)

1. Copy `SKILL.md` and the `references/` folder from OneDrive into this directory.
2. Re-ingest with the generic pipeline:
   ```bash
   python pi_backend/scripts/ingest_skill.py skills/agility-reporting \
       --corpus-name agility_reporting_v1 --content-domain reporting
   ```
3. Deploy as usual — the server already loads `agility_reporting_v1` via
   `SKILL_REGISTRY`.

Once migrated, the skill is version-controlled alongside the code and any machine
(or Claude Code session) can rebuild the corpus without OneDrive access.
