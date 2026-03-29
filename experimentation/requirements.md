This project implements the backend logic for a Unity-based surgical training game that utilizes a Phantom Omni haptic device to provide users with force feedback during simulated procedures. The Unity application serves as the main game interface, while the backend—developed in Python—handles the real-time communication with the haptic device, processes user input, and computes performance metrics.

The backend connects to the Phantom Omni device using OpenHaptics or a similar library, capturing the user's controller movements as they attempt to follow a predefined set of waypoints representing the optimal path for a surgical task. These waypoints are provided as reference data, and the backend is responsible for comparing the user's actual movements to these references to evaluate accuracy, smoothness, and other relevant heuristics.

The system supports multiple scenarios, including training, test1, and test2, each with its own set of waypoints and evaluation criteria. At the end of each run, the backend records detailed performance metrics for later analysis. Reference implementations for device communication and movement tracking can be found in polyline_tracker_3d.py and mouse_demo/sequence_tracker.py.

Key features:

Real-time data acquisition from the Phantom Omni device via Python.
Calculation of movement heuristics (e.g., deviation from path, speed, smoothness).
Scenario management for training and testing phases.
Data logging for post-session analysis.
Integration with Unity for seamless user experience.
This backend is designed to be modular and extensible, allowing for the addition of new heuristics, scenarios, or device support as needed.