"""Automated analysis pipeline for experiment data processing."""
import json
import numpy as np
from scipy import signal
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for web server
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import Dict, Tuple, List
import sys

# Add parent directory to path to import analyze_jitter functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_experiment_data(json_path: str) -> Dict:
    """Load experiment data from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def apply_butterworth_filter(positions: np.ndarray, timestamps: np.ndarray, 
                             cutoff_hz: float = 6.0, order: int = 4) -> np.ndarray:
    """Apply Butterworth low-pass filter to position data."""
    # Compute average sample rate
    dt = np.diff(timestamps)
    avg_dt = np.mean(dt)
    sample_rate = 1.0 / avg_dt
    
    # Design filter
    nyquist = sample_rate / 2
    cutoff_normalized = cutoff_hz / nyquist
    
    # Ensure cutoff is valid
    if cutoff_normalized >= 1.0:
        print(f"Warning: Cutoff frequency {cutoff_hz} Hz is too high for sample rate {sample_rate} Hz")
        cutoff_normalized = 0.9
    
    b, a = signal.butter(order, cutoff_normalized, btype='low', analog=False)
    
    # Apply filter to each axis
    filtered = np.zeros_like(positions)
    for i in range(3):
        filtered[:, i] = signal.filtfilt(b, a, positions[:, i])
    
    return filtered


def compute_jitter_metrics(original: np.ndarray, filtered: np.ndarray) -> Dict:
    """Compute jitter metrics (residual high-frequency noise)."""
    jitter = np.linalg.norm(original - filtered, axis=1)
    
    return {
        'jitter_rms': float(np.sqrt(np.mean(jitter**2))),
        'jitter_mean': float(np.mean(jitter)),
        'jitter_std': float(np.std(jitter)),
        'jitter_max': float(np.max(jitter)),
        'jitter_min': float(np.min(jitter)),
        'jitter_p2p': float(np.max(jitter) - np.min(jitter))
    }


def point_to_segment_distance(point: np.ndarray, seg_start: np.ndarray, 
                              seg_end: np.ndarray) -> float:
    """Compute perpendicular distance from point to line segment."""
    segment_vec = seg_end - seg_start
    point_vec = point - seg_start
    
    segment_length_sq = np.dot(segment_vec, segment_vec)
    
    if segment_length_sq < 1e-10:
        return np.linalg.norm(point_vec)
    
    # Project point onto line
    t = np.dot(point_vec, segment_vec) / segment_length_sq
    t = np.clip(t, 0, 1)
    
    closest_point = seg_start + t * segment_vec
    return np.linalg.norm(point - closest_point)


def compute_lateral_error_metrics(positions: np.ndarray, waypoints: np.ndarray) -> Dict:
    """Compute lateral deviation from ideal path."""
    lateral_errors = []
    
    for pos in positions:
        # Find closest segment
        min_distance = float('inf')
        
        for i in range(len(waypoints) - 1):
            distance = point_to_segment_distance(pos, waypoints[i], waypoints[i + 1])
            min_distance = min(min_distance, distance)
        
        lateral_errors.append(min_distance)
    
    lateral_errors = np.array(lateral_errors)
    
    return {
        'lateral_error_rms': float(np.sqrt(np.mean(lateral_errors**2))),
        'lateral_error_mean': float(np.mean(lateral_errors)),
        'lateral_error_std': float(np.std(lateral_errors)),
        'lateral_error_max': float(np.max(lateral_errors)),
        'lateral_error_min': float(np.min(lateral_errors))
    }


def compute_path_efficiency(positions: np.ndarray, waypoints: np.ndarray) -> Dict:
    """Compute path efficiency metrics."""
    # Ideal path length
    ideal_length = 0.0
    for i in range(len(waypoints) - 1):
        ideal_length += np.linalg.norm(waypoints[i + 1] - waypoints[i])
    
    # Actual path length
    actual_length = 0.0
    for i in range(len(positions) - 1):
        actual_length += np.linalg.norm(positions[i + 1] - positions[i])
    
    efficiency = (ideal_length / actual_length * 100) if actual_length > 0 else 0
    
    return {
        'path_efficiency': float(efficiency),
        'ideal_path_length': float(ideal_length),
        'actual_path_length': float(actual_length),
        'excess_path_length': float(actual_length - ideal_length)
    }


def extract_waypoints_from_data(data: Dict) -> np.ndarray:
    """Extract unique waypoint positions from experiment data."""
    waypoints = []
    seen_indices = set()
    
    for tick in data['ticks']:
        wp_index = tick['waypoint_index']
        if wp_index not in seen_indices:
            waypoints.append([
                tick['target_x'],
                tick['target_y'],
                tick['target_z']
            ])
            seen_indices.add(wp_index)
    
    return np.array(waypoints)


def analyze_experiment(json_path: str, output_dir: Path, 
                       cutoff_hz: float = 6.0) -> Dict:
    """
    Complete analysis pipeline for an experiment.
    
    Returns a dictionary of all computed metrics.
    """
    # Load data
    data = load_experiment_data(json_path)
    
    # Extract positions and timestamps
    ticks = data['ticks']
    
    # Filter out waypoint 0 (starting position)
    filtered_ticks = [t for t in ticks if t['waypoint_index'] > 0]
    
    if not filtered_ticks:
        raise ValueError("No data points after filtering waypoint 0")
    
    timestamps = np.array([t['elapsed_time'] for t in filtered_ticks])
    positions = np.array([[t['device_x'], t['device_y'], t['device_z']] 
                         for t in filtered_ticks])
    
    # Extract waypoints (excluding waypoint 0)
    waypoints = extract_waypoints_from_data(data)
    if len(waypoints) > 1:
        waypoints = waypoints[1:]  # Exclude starting position
    
    # Apply filtering
    filtered_positions = apply_butterworth_filter(positions, timestamps, cutoff_hz)
    
    # Compute all metrics
    metrics = {}
    
    # Jitter metrics
    metrics.update(compute_jitter_metrics(positions, filtered_positions))
    
    # Lateral error metrics
    if len(waypoints) > 1:
        metrics.update(compute_lateral_error_metrics(filtered_positions, waypoints))
    
    # Path efficiency
    if len(waypoints) > 1:
        metrics.update(compute_path_efficiency(filtered_positions, waypoints))
    
    # Task completion metrics
    metrics['total_duration'] = float(data['metadata']['total_duration_seconds'])
    metrics['total_ticks'] = int(data['metadata']['total_ticks'])
    metrics['average_tick_rate'] = float(data['metadata']['average_tick_rate'])
    
    # Generate visualizations
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3D trajectory plot
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot original and filtered trajectories
    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2], 
            'r-', alpha=0.3, linewidth=1, label='Original')
    ax.plot(filtered_positions[:, 0], filtered_positions[:, 1], filtered_positions[:, 2],
            'b-', linewidth=2, label='Filtered')
    
    # Plot waypoints if available
    if len(waypoints) > 1:
        ax.plot(waypoints[:, 0], waypoints[:, 1], waypoints[:, 2],
                'go-', markersize=8, linewidth=2, label='Target Path')
    
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    ax.set_title('3D Trajectory Analysis')
    ax.legend()
    
    trajectory_path = output_dir / 'trajectory_3d.png'
    plt.savefig(trajectory_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Jitter over time plot
    jitter_values = np.linalg.norm(positions - filtered_positions, axis=1)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, jitter_values, 'b-', linewidth=1, alpha=0.7)
    ax.axhline(y=metrics['jitter_rms'], color='r', linestyle='--', 
               label=f"RMS: {metrics['jitter_rms']:.2f} mm")
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Jitter (mm)')
    ax.set_title('Residual Jitter Over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    jitter_path = output_dir / 'jitter_analysis.png'
    plt.savefig(jitter_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Save filtered data
    filtered_data = {
        'metadata': {
            **data['metadata'],
            'filter_cutoff_hz': cutoff_hz,
            'filter_order': 4
        },
        'metrics': metrics,
        'filtered_data': [
            {
                'timestamp': float(timestamps[i]),
                'original': positions[i].tolist(),
                'filtered': filtered_positions[i].tolist()
            }
            for i in range(len(timestamps))
        ]
    }
    
    filtered_json_path = output_dir / 'filtered_data.json'
    with open(filtered_json_path, 'w') as f:
        json.dump(filtered_data, f, indent=2)
    
    return metrics


def generate_comparison_visualization(experiment_ids: List[int], 
                                     experiments_data: List[Dict],
                                     output_path: Path):
    """Generate comparison visualization for multiple experiments."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Experiment Comparison', fontsize=16, fontweight='bold')
    
    # Extract metrics
    labels = [f"Exp {exp['id']}\n({exp['participant_id']})" 
              for exp in experiments_data]
    
    # Path efficiency
    efficiencies = [exp.get('path_efficiency', 0) for exp in experiments_data]
    axes[0, 0].bar(labels, efficiencies, color='skyblue')
    axes[0, 0].set_ylabel('Path Efficiency (%)')
    axes[0, 0].set_title('Path Efficiency Comparison')
    axes[0, 0].grid(axis='y', alpha=0.3)
    
    # Duration
    durations = [exp.get('total_duration', 0) for exp in experiments_data]
    axes[0, 1].bar(labels, durations, color='lightcoral')
    axes[0, 1].set_ylabel('Duration (s)')
    axes[0, 1].set_title('Task Duration Comparison')
    axes[0, 1].grid(axis='y', alpha=0.3)
    
    # RMS Jitter
    jitters = [exp.get('jitter_rms', 0) for exp in experiments_data]
    axes[1, 0].bar(labels, jitters, color='lightgreen')
    axes[1, 0].set_ylabel('RMS Jitter (mm)')
    axes[1, 0].set_title('Jitter Comparison')
    axes[1, 0].grid(axis='y', alpha=0.3)
    
    # Lateral Error
    errors = [exp.get('lateral_error_rms', 0) for exp in experiments_data]
    axes[1, 1].bar(labels, errors, color='plum')
    axes[1, 1].set_ylabel('RMS Lateral Error (mm)')
    axes[1, 1].set_title('Lateral Error Comparison')
    axes[1, 1].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
