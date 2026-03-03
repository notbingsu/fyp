# Project Overview

This repository contains three focused efforts:

**mouse_demo** demonstrates interaction physics between two users on the Phantom Omni. It captures paired input and response behavior to study how forces and motion interact across users in a shared haptic task.

**opengl_movement** simulates movement in a 3D environment model with navigation implemented using Three.js. It includes a controllable cursor, third-person camera, and basic scene setup for testing navigation dynamics.

**web_gui** provides a modern web-based interface for conducting haptic experiments, automatically analyzing results, and managing experiment data with comprehensive visualizations and reporting capabilities.

## web_gui - Web Interface for Haptic Experiments

**Purpose:** Streamlined workflow for conducting haptic guidance experiments with automatic data processing, visualization, and reporting.

### Quick Start

```bash
# Install dependencies
cd fyp
pip install -r requirements.txt

# Start the web server
cd web_gui
python3 run_server.py
```

The web interface will automatically open at http://localhost:5000

### Features

- 🚀 **Easy Launch**: Configure and start experiments with a user-friendly interface
- 📊 **Automatic Analysis**: Results processed immediately after experiment completion
- 📈 **Rich Visualizations**: 3D trajectory plots, jitter analysis, performance metrics
- 📚 **History Management**: Track multiple experiments, filter by participant, compare results
- 📄 **Export Reports**: Generate PDF reports and CSV data exports
- 💾 **Persistent Storage**: SQLite database for experiment tracking and metrics

### Workflow

1. **Launch Screen** → Enter participant ID and configure haptic parameters
2. **Experiment Execution** → Complete the 3D polyline tracking task in Pygame window
3. **Results Display** → View metrics, visualizations, and detailed statistics
4. **History Dashboard** → Browse past experiments, compare performance, export data

### Key Components

- `app.py`: Flask web server with REST API endpoints
- `database.py`: SQLite database for experiment storage
- `analysis_pipeline.py`: Automated data processing with Butterworth filtering
- `templates/`: HTML pages (launch, results, history)
- `static/`: CSS and JavaScript for the web interface

For detailed documentation, see [web_gui/README.md](web_gui/README.md)

## mouse_demo usage

**Purpose:** haptic guidance and interaction physics between two Phantom Omni users, with experiment logging and visualization.

- **linedemo.py**: main interactive demo. Runs the haptic loop, applies guidance forces, and renders the target path for live interaction.
- **sequence_tracker.py**: timed experiment runner. Logs distance/error metrics to JSON for analysis.
- **visualization.py**: post-process plots. Generates charts from the JSON output (distance over time, trajectories, component plots).
