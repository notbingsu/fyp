"""Database layer for experiment tracking and metrics storage."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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
    """Initialize database tables if they don't exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT NOT NULL,
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


def create_experiment(participant_id: str, haptic_enabled: bool, 
                     k_xy: float, k_z: float) -> int:
    """Create a new experiment record and return its ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO experiments 
            (participant_id, timestamp, haptic_enabled, k_xy, k_z, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (participant_id, timestamp, int(haptic_enabled), k_xy, k_z, timestamp))
        
        conn.commit()
        return cursor.lastrowid


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
        
        if row:
            return dict(row)
        return None


def get_experiment_with_metrics(experiment_id: int) -> Optional[Dict]:
    """Get experiment with its metrics."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.*, m.*
            FROM experiments e
            LEFT JOIN metrics m ON e.id = m.experiment_id
            WHERE e.id = ?
        ''', (experiment_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None


def get_all_experiments(participant_id: Optional[str] = None) -> List[Dict]:
    """Get all experiments, optionally filtered by participant."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if participant_id:
            cursor.execute('''
                SELECT e.*, m.jitter_rms, m.lateral_error_rms, 
                       m.path_efficiency, m.total_duration
                FROM experiments e
                LEFT JOIN metrics m ON e.id = m.experiment_id
                WHERE e.participant_id = ?
                ORDER BY e.timestamp DESC
            ''', (participant_id,))
        else:
            cursor.execute('''
                SELECT e.*, m.jitter_rms, m.lateral_error_rms, 
                       m.path_efficiency, m.total_duration
                FROM experiments e
                LEFT JOIN metrics m ON e.id = m.experiment_id
                ORDER BY e.timestamp DESC
            ''')
        
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


def get_participant_statistics(participant_id: str) -> Dict:
    """Get aggregate statistics for a participant."""
    with get_db() as conn:
        cursor = conn.cursor()
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
