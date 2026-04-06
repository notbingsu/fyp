# CDE4301 Final Year Project — Haptic Guidance Research

Research project investigating haptic guidance for 3D polyline tracking tasks using the Phantom Omni device.

## Repository Structure

```
fyp/
├── experiment/          # Experiment setup and execution
│   ├── experiment_runner.py   # Main experiment runner (Pygame + haptics)
│   ├── design.md              # Experimental design documentation
│   ├── utils/                 # Shared utilities (device, physics, waypoints)
│   ├── waypoints/             # Path definition CSVs (Training, Test1, Test2)
│   └── unity/                 # Unity C# integration scripts
│
├── web_gui/             # Flask web interface for running and reviewing experiments
│   ├── run_server.py          # Start here
│   ├── app.py                 # REST API endpoints
│   ├── database.py            # SQLite experiment storage
│   ├── analysis_pipeline.py   # Butterworth filtering, metrics, visualizations
│   ├── analysis_output/       # Per-session generated outputs (gitignored, P001/Test1 sample kept)
│   └── README.md              # Detailed web GUI documentation
│
├── data/                # Collected experiment data
│   ├── results/               # Raw per-participant CSVs (P001 sample kept, P002–P018 gitignored)
│   ├── experiment_metadata.csv
│   └── rename_results.py      # Utility to normalise result filenames
│
├── analysis/            # Analysis notebooks and outputs
│   ├── analysis.ipynb         # Main analysis notebook
│   └── figures/               # Generated plots (trajectory overlay, jitter comparison, etc.)
│
├── demos/               # Early prototypes (not part of main experiment)
│   ├── mouse_demo/            # Phantom Omni two-user interaction demo
│   └── opengl_movement/       # Three.js 3D navigation prototype
│
├── pyhaptics.py         # Core haptics library wrapper
└── requirements.txt
```

## Quick Start

### Running an experiment

```bash
pip install -r requirements.txt
cd web_gui
python3 run_server.py
```

The web interface opens at http://localhost:5000. Enter a participant ID, configure haptic parameters, and start the experiment. Results and visualisations are available immediately after completion.

See [web_gui/README.md](web_gui/README.md) for full documentation.

### Running the Unity game

1. Unzip `FYP Game v03.zip`
2. Run `Surgery Haptic Training.exe` inside the extracted folder
3. Connect the Phantom Omni before launching — the game will detect it automatically

Run data is written inside the extracted game folder:
- **`waypoints/`** — raw movement CSVs, one file per session
- **`experiment_data/`** — meta metrics per trial (completion time, errors, etc.)

The web GUI (`web_gui/run_server.py`) can then be used to analyse and review the collected data.

### Running the experiment directly (no web GUI)

```bash
python3 experiment/experiment_runner.py
```

### Analysing results

Open [analysis/analysis.ipynb](analysis/analysis.ipynb) in Jupyter. The notebook reads from `data/results/` and produces the plots saved in `analysis/figures/`.

## Data

Raw movement data CSVs are stored in `data/results/<participant_id>/`. Each file covers one session and captures:

| Column | Description |
|---|---|
| `time_s` | Elapsed time (seconds) |
| `pos_x/y/z` | Haptic device tip position (world frame) |
| `dist_to_target` | Distance to current waypoint |
| `force_x/y/z` | Guidance force applied |
| `collision_event` | Collision flag |
| `click_event` | Waypoint click flag |

Session naming convention: `{participant}_{condition}_{phase}_{date}_{time}.csv`

Only `P001` data is committed as a schema reference. All other participant data is gitignored due to size.

Processed outputs (filtered signals, trajectory plots, jitter plots) live in `web_gui/analysis_output/<participant_id>/<session>/`.

## Demos

`demos/mouse_demo/` — an earlier prototype using the Phantom Omni with two simultaneous users. Contains its own experiment data and report plots.

`demos/opengl_movement/` — a Three.js 3D environment used to prototype navigation mechanics before the Unity integration.
