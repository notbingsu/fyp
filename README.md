# Project Overview

This repository contains two focused efforts.

**mouse_demo** demonstrates interaction physics between two users on the Phantom Omni. It captures paired input and response behavior to study how forces and motion interact across users in a shared haptic task.

**opengl_movement** simulates movement in a 3D environment model with navigation implemented using Three.js. It includes a controllable cursor, third-person camera, and basic scene setup for testing navigation dynamics.

## mouse_demo usage

**Purpose:** haptic guidance and interaction physics between two Phantom Omni users, with experiment logging and visualization.

- **linedemo.py**: main interactive demo. Runs the haptic loop, applies guidance forces, and renders the target path for live interaction.
- **sequence_tracker.py**: timed experiment runner. Logs distance/error metrics to JSON for analysis.
- **visualization.py**: post-process plots. Generates charts from the JSON output (distance over time, trajectories, component plots).
