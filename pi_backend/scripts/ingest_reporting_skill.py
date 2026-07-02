"""Ingest the Agility Reporting skill via the generic ingest_skill pipeline.

The reporting skill source currently lives on OneDrive (outside the repo).
Once it is migrated into skills/agility-reporting/, run the generic script
instead:

    python pi_backend/scripts/ingest_skill.py skills/agility-reporting \
        --corpus-name agility_reporting_v1 --content-domain reporting
"""

import argparse
from pathlib import Path

from ingest_skill import ingest_skill

DEFAULT_SKILL_DIR = Path(r"C:\Users\indha\OneDrive - Beisser Lumber\ai\skills\agility-reporting")


def main():
    parser = argparse.ArgumentParser(description="Ingest the Agility Reporting skill")
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=DEFAULT_SKILL_DIR,
        help="Reporting skill folder (default: OneDrive location)",
    )
    args = parser.parse_args()

    ingest_skill(
        skill_dir=args.skill_dir,
        corpus_name="agility_reporting_v1",
        content_domain="reporting",
    )


if __name__ == "__main__":
    main()
