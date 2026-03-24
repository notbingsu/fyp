"""
CSV waypoint loader for haptic experiment scenarios.
Each CSV file should contain rows of [x, y, z] coordinates (header optional).
"""
import csv
import os

def load_waypoints_from_csv(csv_path):
    waypoints = []
    with open(csv_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Skip header if present (assume header if non-numeric)
            if not row or not all(item.replace('.', '', 1).replace('-', '', 1).isdigit() for item in row[:3]):
                continue
            waypoints.append([float(row[0]), float(row[1]), float(row[2])])
    return waypoints

def discover_waypoint_sets(directory):
    """Return dict: {scenario_name: waypoints_list} for all CSVs in directory."""
    sets = {}
    for fname in os.listdir(directory):
        if fname.lower().endswith('.csv'):
            scenario = os.path.splitext(fname)[0]
            sets[scenario] = load_waypoints_from_csv(os.path.join(directory, fname))
    return sets
