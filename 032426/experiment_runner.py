"""
Main experiment runner for haptic guidance scenarios.
"""
import time
import argparse
from utils.device import device_state, state_callback
from utils.physics import PolylinePath3D, PhysicsEngine3D
from utils.experiment import ExperimentData
from pyOpenHaptics.hd_device import HapticDevice
import pyOpenHaptics.hd as hd

# Example waypoints for scenarios (replace with real data as needed)
WAYPOINTS = {
    "training": [
        [0, 0, 0], [20, 15, 8], [35, 30, 18], [45, 45, 30], [50, 60, 40],
        [45, 75, 48], [30, 85, 52], [10, 90, 50], [-10, 88, 45], [-30, 82, 38],
        [0, 0, 0]  # Loop back for demo
    ],
    "test1": [
        [0, 0, 0], [20, 20, 10], [40, 40, 20], [60, 60, 30], [80, 80, 40]
    ],
    "test2": [
        [0, 0, 0], [-20, -20, -10], [-40, -40, -20], [-60, -60, -30], [-80, -80, -40]
    ]
}

def run_experiment(scenario, duration=30, fps=60, participant_id="test", haptic_enabled=True):
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
    parser.add_argument('--scenario', choices=WAYPOINTS.keys(), default='training')
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
