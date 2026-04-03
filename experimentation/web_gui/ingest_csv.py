"""Ingest experiment CSV files into the database.

Usage:
    python ingest_csv.py <participant_dir>

Example:
    python ingest_csv.py "../../data_analysis/Results/P001"

Filename format: {PID}_{Condition}_{Scenario}_{DDMmmYYYY}_{HH-MM-SS}.csv
  e.g. P001_ExpertControlled_Test1_30Mar2026_23-22-16.csv
Waypoints live in: ../waypoints/{Scenario}.csv  (Training.csv, Test1.csv, Test2.csv)
"""
import sys
import re
from datetime import datetime
from pathlib import Path

# Allow importing sibling modules
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_pipeline import analyze_experiment_csv
from database import create_experiment_csv, save_metrics

WAYPOINTS_DIR = Path(__file__).parent.parent / 'waypoints'

# e.g. P001_ExpertControlled_Test1_30Mar2026_23-22-16.csv
FILENAME_RE = re.compile(
    r'^(?P<pid>[^_]+)_(?P<condition>[^_]+)_(?P<scenario>[^_]+)_'
    r'(?P<date>\d{2}[A-Za-z]{3}\d{4})_(?P<time>\d{2}-\d{2}-\d{2})\.csv$'
)


def ingest_participant(participant_dir: Path):
    csv_files = sorted(participant_dir.glob('*.csv'))
    if not csv_files:
        print(f"No CSV files found in {participant_dir}")
        return

    print(f"Found {len(csv_files)} file(s) in {participant_dir.name}")

    for csv_path in csv_files:
        m = FILENAME_RE.match(csv_path.name)
        if not m:
            print(f"  SKIP (unrecognised filename): {csv_path.name}")
            continue

        pid = m.group('pid')
        condition = m.group('condition')
        scenario = m.group('scenario')
        dt = datetime.strptime(f"{m.group('date')} {m.group('time').replace('-', ':')}", '%d%b%Y %H:%M:%S')
        timestamp = dt.isoformat()

        # Calibration runs share the Training waypoints (no intervention, same path)
        waypoint_scenario = 'Training' if scenario == 'Calibration' else scenario
        reference_csv = WAYPOINTS_DIR / f'{waypoint_scenario}.csv'
        if not reference_csv.exists():
            print(f"  SKIP (no reference path for scenario '{scenario}'): {csv_path.name}")
            continue

        output_dir = Path(__file__).parent / 'analysis_output' / pid / csv_path.stem
        print(f"  Processing {csv_path.name} ...", end=' ', flush=True)

        try:
            metrics = analyze_experiment_csv(
                str(csv_path),
                str(reference_csv),
                output_dir,
            )

            exp_id = create_experiment_csv(
                participant_id=pid,
                condition=condition,
                scenario=scenario,
                raw_data_path=str(csv_path),
                duration=metrics['total_duration'],
                timestamp=timestamp,
            )
            save_metrics(exp_id, metrics)

            print(f"OK  (id={exp_id}, duration={metrics['total_duration']:.1f}s, "
                  f"lateral_rms={metrics['lateral_error_rms']:.4f}m)")

        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    participant_dir = Path(sys.argv[1]).resolve()
    if not participant_dir.is_dir():
        print(f"Not a directory: {participant_dir}")
        sys.exit(1)

    ingest_participant(participant_dir)
