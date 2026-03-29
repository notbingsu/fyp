"""Database layer for experiment tracking and metrics storage."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import contextlib

DB_PATH = Path(__file__).parent / "experiments.db"


@contextlib.contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database tables if they don't exist, and migrate if needed."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                participant_id TEXT NOT NULL,
                scenario TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL,
                haptic_enabled INTEGER NOT NULL,
                k_xy REAL NOT NULL,
                k_z REAL NOT NULL,
                duration REAL,
                status TEXT NOT NULL DEFAULT 'pending',
                raw_data_path TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                jitter_rms REAL,
                jitter_mean REAL,
                jitter_std REAL,
                jitter_max REAL,
                jitter_min REAL,
                jitter_p2p REAL,
                lateral_error_rms REAL,
                lateral_error_mean REAL,
                lateral_error_std REAL,
                lateral_error_max REAL,
                lateral_error_min REAL,
                path_efficiency REAL,
                ideal_path_length REAL,
                actual_path_length REAL,
                excess_path_length REAL,
                total_duration REAL,
                total_ticks INTEGER,
                average_tick_rate REAL,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id)
            )
        ''')

        conn.commit()

        # Migrate existing DB: add columns if missing
        for col, definition in [('run_id', 'TEXT'), ('scenario', "TEXT NOT NULL DEFAULT ''")]:
            try:
                cursor.execute(f'ALTER TABLE experiments ADD COLUMN {col} {definition}')
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists


def create_experiment(participant_id: str, scenario: str, haptic_enabled: bool,
                      k_xy: float, k_z: float) -> int:
    """Create a new experiment record and return its ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        run_id = f"{participant_id}_{scenario}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        cursor.execute('''
            INSERT INTO experiments
            (run_id, participant_id, scenario, timestamp, haptic_enabled, k_xy, k_z, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (run_id, participant_id, scenario, timestamp, int(haptic_enabled), k_xy, k_z, timestamp))

        conn.commit()
        return cursor.lastrowid


def get_run_id(experiment_id: int) -> Optional[str]:
    """Get the run_id for an experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT run_id FROM experiments WHERE id = ?', (experiment_id,))
        row = cursor.fetchone()
        return row['run_id'] if row else None


def update_experiment_status(experiment_id: int, status: str,
                             duration: Optional[float] = None,
                             raw_data_path: Optional[str] = None):
    """Update experiment status and optional metadata."""
    with get_db() as conn:
        cursor = conn.cursor()

        if duration is not None and raw_data_path is not None:
            cursor.execute('''
                UPDATE experiments
                SET status = ?, duration = ?, raw_data_path = ?
                WHERE id = ?
            ''', (status, duration, raw_data_path, experiment_id))
        else:
            cursor.execute('''
                UPDATE experiments
                SET status = ?
                WHERE id = ?
            ''', (status, experiment_id))

        conn.commit()


def save_metrics(experiment_id: int, metrics: Dict):
    """Save computed metrics for an experiment."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO metrics (
                experiment_id, jitter_rms, jitter_mean, jitter_std,
                jitter_max, jitter_min, jitter_p2p,
                lateral_error_rms, lateral_error_mean, lateral_error_std,
                lateral_error_max, lateral_error_min,
                path_efficiency, ideal_path_length, actual_path_length,
                excess_path_length, total_duration, total_ticks, average_tick_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            experiment_id,
            metrics.get('jitter_rms'),
            metrics.get('jitter_mean'),
            metrics.get('jitter_std'),
            metrics.get('jitter_max'),
            metrics.get('jitter_min'),
            metrics.get('jitter_p2p'),
            metrics.get('lateral_error_rms'),
            metrics.get('lateral_error_mean'),
            metrics.get('lateral_error_std'),
            metrics.get('lateral_error_max'),
            metrics.get('lateral_error_min'),
            metrics.get('path_efficiency'),
            metrics.get('ideal_path_length'),
            metrics.get('actual_path_length'),
            metrics.get('excess_path_length'),
            metrics.get('total_duration'),
            metrics.get('total_ticks'),
            metrics.get('average_tick_rate')
        ))

        conn.commit()


def get_experiment(experiment_id: int) -> Optional[Dict]:
    """Get experiment details by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM experiments WHERE id = ?', (experiment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_experiment_by_run_id(run_id: str) -> Optional[Dict]:
    """Get experiment details by human-readable run_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM experiments WHERE run_id = ?', (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_experiment_with_metrics(experiment_id: int) -> Optional[Dict]:
    """Get experiment with its metrics by integer ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, m.*
            FROM experiments e
            LEFT JOIN metrics m ON e.id = m.experiment_id
            WHERE e.id = ?
        ''', (experiment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_experiment_with_metrics_by_run_id(run_id: str) -> Optional[Dict]:
    """Get experiment with its metrics by run_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, m.*
            FROM experiments e
            LEFT JOIN metrics m ON e.id = m.experiment_id
            WHERE e.run_id = ?
        ''', (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_experiments(participant_id: Optional[str] = None,
                        scenario: Optional[str] = None) -> List[Dict]:
    """Get all experiments, optionally filtered by participant and/or scenario."""
    with get_db() as conn:
        cursor = conn.cursor()

        conditions = []
        params = []
        if participant_id:
            conditions.append('e.participant_id = ?')
            params.append(participant_id)
        if scenario:
            conditions.append('e.scenario = ?')
            params.append(scenario)

        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

        cursor.execute(f'''
            SELECT e.*, m.jitter_rms, m.lateral_error_rms,
                   m.path_efficiency, m.total_duration
            FROM experiments e
            LEFT JOIN metrics m ON e.id = m.experiment_id
            {where}
            ORDER BY e.timestamp DESC
        ''', params)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_experiments_by_participant_scenario(participant_id: str,
                                            scenario: str) -> List[Dict]:
    """Get all experiments for a participant+scenario, ordered chronologically.

    Use this for plotting metric progression across attempts.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, m.*
            FROM experiments e
            LEFT JOIN metrics m ON e.id = m.experiment_id
            WHERE e.participant_id = ? AND e.scenario = ? AND e.status = 'completed'
            ORDER BY e.timestamp ASC
        ''', (participant_id, scenario))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_experiments_by_ids(experiment_ids: List[int]) -> List[Dict]:
    """Get multiple experiments with metrics for comparison."""
    with get_db() as conn:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(experiment_ids))

        cursor.execute(f'''
            SELECT e.*, m.*
            FROM experiments e
            LEFT JOIN metrics m ON e.id = m.experiment_id
            WHERE e.id IN ({placeholders})
            ORDER BY e.timestamp
        ''', experiment_ids)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_participant_statistics(participant_id: str,
                               scenario: Optional[str] = None) -> Dict:
    """Get aggregate statistics for a participant, optionally scoped to a scenario."""
    with get_db() as conn:
        cursor = conn.cursor()

        if scenario:
            cursor.execute('''
                SELECT
                    COUNT(*) as total_experiments,
                    AVG(m.path_efficiency) as avg_efficiency,
                    AVG(m.total_duration) as avg_duration,
                    AVG(m.jitter_rms) as avg_jitter,
                    AVG(m.lateral_error_rms) as avg_lateral_error
                FROM experiments e
                LEFT JOIN metrics m ON e.id = m.experiment_id
                WHERE e.participant_id = ? AND e.scenario = ? AND e.status = 'completed'
            ''', (participant_id, scenario))
        else:
            cursor.execute('''
                SELECT
                    COUNT(*) as total_experiments,
                    AVG(m.path_efficiency) as avg_efficiency,
                    AVG(m.total_duration) as avg_duration,
                    AVG(m.jitter_rms) as avg_jitter,
                    AVG(m.lateral_error_rms) as avg_lateral_error
                FROM experiments e
                LEFT JOIN metrics m ON e.id = m.experiment_id
                WHERE e.participant_id = ? AND e.status = 'completed'
            ''', (participant_id,))

        row = cursor.fetchone()
        return dict(row) if row else {}


# Initialize database on module import
init_database()
