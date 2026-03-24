"""
Main experiment runner for haptic guidance scenarios.
"""
import time
import argparse

from utils.device import device_state, state_callback
from utils.physics import PolylinePath3D, PhysicsEngine3D
from utils.experiment import ExperimentData
from utils.waypoints import discover_waypoint_sets
from pyOpenHaptics.hd_device import HapticDevice
import pyOpenHaptics.hd as hd
import os

# Directory containing waypoint CSV files
WAYPOINTS_DIR = os.path.join(os.path.dirname(__file__), "waypoints")
WAYPOINTS = discover_waypoint_sets(WAYPOINTS_DIR)


def run_experiment(scenario, duration=30, fps=60, participant_id="test", haptic_enabled=True):
    if scenario not in WAYPOINTS:
        raise ValueError(f"Scenario '{scenario}' not found in waypoints directory '{WAYPOINTS_DIR}'.")
    waypoints = WAYPOINTS[scenario]
    path = PolylinePath3D(waypoints)
    physics = PhysicsEngine3D()
    data = ExperimentData(fps=fps, participant_id=participant_id, haptic_enabled=haptic_enabled)
    device = HapticDevice(device_name="Default Device", callback=state_callback)
    time.sleep(0.2)
    data.start_time = time.time()
    start = time.time()
    while True:
        now = time.time()
        elapsed = now - start
        if elapsed > duration or path.is_at_endpoint(device_state.position):
            break
        target, dist, progress = path.update(device_state.position)
        force = physics.calculate_guidance_force(device_state.position, target) if haptic_enabled else [0,0,0]
        device_state.force = force
        data.ticks.append({
            "t": elapsed,
            "pos": list(device_state.position),
            "target": target,
            "dist": dist,
            "progress": progress,
            "force": force
        })
        time.sleep(1.0 / fps)
    data.end_time = time.time()
    data.duration = data.end_time - data.start_time
    device.close()
    data.save(f"experiment_{scenario}_{participant_id}.json")
    print(f"Experiment complete. Data saved.")


def main():
    parser = argparse.ArgumentParser(description="Run haptic experiment scenario.")
    parser.add_argument('--scenario', choices=list(WAYPOINTS.keys()), default=next(iter(WAYPOINTS.keys()), None))
    parser.add_argument('--duration', type=int, default=30)
    parser.add_argument('--fps', type=int, default=60)
    parser.add_argument('--participant', type=str, default='test')
    parser.add_argument('--no-haptic', action='store_true')
    args = parser.parse_args()
    run_experiment(
        scenario=args.scenario,
        duration=args.duration,
        fps=args.fps,
        participant_id=args.participant,
        haptic_enabled=not args.no_haptic
    )

if __name__ == "__main__":
    main()
