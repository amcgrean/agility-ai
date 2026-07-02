# Beisser AI Skills

A **skill** is a small, curated knowledge pack that powers an expert mode in Beisser AI.
Unlike the main Agility docs corpus (2319 chunks, FAISS-retrieved), a skill corpus is
small enough to be sent to the LLM **in full** on every question in that mode — no
vector search, no retrieval misses.

## Layout

```
skills/
  <skill-name>/
    SKILL.md            # Scope, terminology, and answering guidance for the skill
    references/         # One markdown file per topic — each becomes one chunk
      *.md
```

## Current skills

| Skill | Mode | Corpus | Status |
|-------|------|--------|--------|
| `agility-reporting` | `reporting` | `agility_reporting_v1` | Source still on OneDrive — see its README |
| `agility-sales-orders` | `sales_orders` | `agility_sales_orders_v1` | In repo — draft knowledge pack, expand with verified procedures |

## Adding or updating a skill

1. **Author content** under `skills/<skill-name>/` (SKILL.md + `references/*.md`).
   Keep each reference file focused on one topic; the whole corpus goes into the
   prompt, so total size matters more than chunk boundaries.
2. **Ingest** it into a corpus:
   ```bash
   python pi_backend/scripts/ingest_skill.py skills/<skill-name>
   ```
   This writes `pi_backend/ingest_output/<corpus>/chunks.jsonl` (gitignored —
   regenerate before each deploy).
3. **Register the mode** (new skills only):
   - `pi_backend/server.py` → add to `SKILL_REGISTRY`
   - `pi_backend/providers.py` → add a prompt profile to `SKILL_PROMPT_PROFILES`
   - `src/skills.jsx` → add a frontend entry (route, nav label, theme, prompt cards)
4. **Deploy**: include the corpus `chunks.jsonl` in the deploy zip (see the deploy
   steps in `CLAUDE.md`), then restart the service.
5. **Verify**: `GET /skills` on the Pi shows each mode with its chunk count and
   `ready: true` once the corpus is loaded.

## Content guidelines

- Answer-shaped content beats raw notes: write the way you'd want the bot to answer.
- Mark Beisser-specific policy explicitly (the prompt tells the model to present
  policy as policy, not as an Agility default).
- Mark anything unverified with a `> **Verify:**` note — the model is instructed to
  surface uncertainty rather than guess.
- The feedback loop still applies: corrections submitted in the UI are stored, but
  the durable fix for a skill mode is editing these files and re-ingesting.
