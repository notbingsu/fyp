"""
CSV waypoint loader for haptic experiment scenarios.
Each CSV file must contain columns: time_s, joint_x, joint_y, joint_z (header required).
Only joint_x, joint_y, joint_z are used as waypoints.
"""
import csv
import os

def load_waypoints_from_csv(csv_path):
    waypoints = []
    with open(csv_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        required = ['time_s', 'joint_x', 'joint_y', 'joint_z']
        if not reader.fieldnames or not all(col in reader.fieldnames for col in required):
            raise ValueError(f"CSV {csv_path} must contain columns: {required}")
        for row in reader:
            try:
                # Only extract joint_x, joint_y, joint_z
                x = float(row['joint_x'])
                y = float(row['joint_y'])
                z = float(row['joint_z'])
                waypoints.append([x, y, z])
            except (ValueError, KeyError):
                continue
    return waypoints

def discover_waypoint_sets(directory):
    """Return dict: {scenario_name: waypoints_list} for all CSVs in directory."""
    sets = {}
    for fname in os.listdir(directory):
        if fname.lower().endswith('.csv'):
            scenario = os.path.splitext(fname)[0]
            sets[scenario] = load_waypoints_from_csv(os.path.join(directory, fname))
    return sets
