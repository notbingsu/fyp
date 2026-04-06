"""Rename result CSV files from YYYY-MM-DD_HH-MM-SS to DDMmmYYYY_HH-MM-SS.

Usage:
    python rename_results.py [--dry-run]

Example:
    P001_ExpertControlled_Training_2026-03-30_23-23-43.csv
    → P001_ExpertControlled_Training_30Mar2026_23-23-43.csv
"""
import re
import sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path(__file__).parent / 'Results'

OLD_RE = re.compile(
    r'^(?P<prefix>.+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})(?P<ext>\.csv)$'
)


def reformat_filename(name: str) -> str | None:
    m = OLD_RE.match(name)
    if not m:
        return None
    dt = datetime.strptime(f"{m.group('date')} {m.group('time').replace('-', ':')}", '%Y-%m-%d %H:%M:%S')
    new_date = dt.strftime('%d%b%Y')   # e.g. 30Mar2026
    return f"{m.group('prefix')}_{new_date}_{m.group('time')}{m.group('ext')}"


def main(dry_run: bool):
    renamed = 0
    skipped = 0
    for csv_path in sorted(RESULTS_DIR.rglob('*.csv')):
        new_name = reformat_filename(csv_path.name)
        if new_name is None:
            print(f"  SKIP (no match): {csv_path.name}")
            skipped += 1
            continue
        new_path = csv_path.parent / new_name
        if dry_run:
            print(f"  DRY  {csv_path.name}  →  {new_name}")
        else:
            csv_path.rename(new_path)
            print(f"  OK   {csv_path.name}  →  {new_name}")
        renamed += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Renamed {renamed}, skipped {skipped}.")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    main(dry_run)
