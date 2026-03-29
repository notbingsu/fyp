"""
Main experiment runner for haptic guidance scenarios.
"""
import time
import argparse
import threading
from typing import Optional

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


def run_experiment(scenario, duration=30, fps=60, participant_id="test",
                   haptic_enabled=True, stop_event: Optional[threading.Event] = None,
                   output_path: Optional[str] = None):
    """Run a haptic guidance experiment.

    Args:
        scenario: Waypoint scenario name (must exist in WAYPOINTS_DIR).
        duration: Maximum duration in seconds before auto-stopping.
        fps: Target recording frame rate.
        participant_id: Identifier for the participant.
        haptic_enabled: Whether to apply force guidance.
        stop_event: Optional threading.Event; when set, the recording loop exits early.
        output_path: Path to save the JSON output. Defaults to
                     experiment_{scenario}_{participant_id}.json in the CWD.

    Returns:
        str: Absolute path to the saved JSON file.
    """
    if scenario not in WAYPOINTS:
        raise ValueError(f"Scenario '{scenario}' not found in waypoints directory '{WAYPOINTS_DIR}'.")

    waypoints = WAYPOINTS[scenario]
    path = PolylinePath3D(waypoints)
    physics = PhysicsEngine3D()
    data = ExperimentData(fps=fps, participant_id=participant_id, scenario=scenario, haptic_enabled=haptic_enabled)
    device = HapticDevice(device_name="Default Device", callback=state_callback)

    while len(device_state.position) < 3:
        time.sleep(0.01)
    data.start_time = time.time()
    start = time.time()

    while True:
        now = time.time()
        elapsed = now - start
        stopped_early = stop_event is not None and stop_event.is_set()
        if elapsed > duration or path.is_at_endpoint(device_state.position) or stopped_early:
            break
        target, dist, progress, waypoint_index = path.update(device_state.position)
        force = physics.calculate_guidance_force(device_state.position, target) if haptic_enabled else [0, 0, 0]
        device_state.force = force
        pos = device_state.position
        data.ticks.append({
            "elapsed_time": elapsed,
            "device_x": pos[0],
            "device_y": pos[1],
            "device_z": pos[2],
            "target_x": target[0],
            "target_y": target[1],
            "target_z": target[2],
            "waypoint_index": waypoint_index,
            "dist": dist,
            "progress": progress,
            "force": force
        })
        time.sleep(1.0 / fps)

    data.end_time = time.time()
    data.duration = data.end_time - data.start_time
    device.close()

    if output_path is None:
        output_path = f"experiment_{scenario}_{participant_id}.json"

    data.save(output_path)
    print(f"Experiment complete. Data saved to {output_path}")
    return os.path.abspath(output_path)


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
