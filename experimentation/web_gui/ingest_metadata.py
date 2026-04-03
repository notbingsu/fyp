"""Ingest experiment_metadata.csv into the metrics table (collisions, wasted_clicks).

Matches metadata rows to DB experiments by participant_id + ISO timestamp.

Usage:
    python ingest_metadata.py [path/to/experiment_metadata.csv]

Defaults to ../../data_analysis/experiment_metadata.csv relative to this script.
"""
import sys
import csv
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import get_db, init_database

DEFAULT_METADATA = Path(__file__).parent.parent.parent / 'data_analysis' / 'experiment_metadata.csv'


def parse_iso(ts_str: str) -> str:
    """Convert YYYY-MM-DD_HH-MM-SS to ISO format YYYY-MM-DDTHH:MM:SS."""
    return datetime.strptime(ts_str, '%Y-%m-%d_%H-%M-%S').isoformat()


def ingest(metadata_path: Path):
    with open(metadata_path, newline='') as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows from {metadata_path.name}")

    matched = 0
    skipped = 0

    with get_db() as conn:
        cursor = conn.cursor()

        for row in rows:
            try:
                iso_ts = parse_iso(row['timestamp'])
            except ValueError:
                print(f"  SKIP (bad timestamp): {row['timestamp']}")
                skipped += 1
                continue

            cursor.execute(
                'SELECT id FROM experiments WHERE participant_id = ? AND timestamp = ?',
                (row['participant_id'], iso_ts)
            )
            exp = cursor.fetchone()
            if exp is None:
                print(f"  SKIP (no experiment match): {row['participant_id']} @ {iso_ts}")
                skipped += 1
                continue

            cursor.execute(
                'UPDATE metrics SET collisions = ?, wasted_clicks = ? WHERE experiment_id = ?',
                (int(row['collisions']), int(row['wasted_clicks']), exp['id'])
            )
            matched += 1

        conn.commit()

    print(f"\nUpdated {matched} metrics rows, skipped {skipped}.")


if __name__ == '__main__':
    init_database()
    metadata_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_METADATA
    if not metadata_path.exists():
        print(f"File not found: {metadata_path}")
        sys.exit(1)
    ingest(metadata_path)
