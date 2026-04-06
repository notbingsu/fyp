# Haptic Experiment Web GUI

A modern web-based interface for conducting haptic guidance experiments, automatically analyzing results, and managing experiment data.

## Features

✨ **Launch Interface**
- Configure experiment parameters (participant ID, haptic gains)
- Enable/disable haptic guidance
- Advanced parameter tuning (k_xy, k_z stiffness values)
- Real-time experiment status tracking

📊 **Results Dashboard**
- Automatic analysis after experiment completion
- Key metrics: Path Efficiency, Task Duration, Jitter, Lateral Error
- Interactive 3D trajectory visualizations
- Detailed performance statistics
- Export reports as PDF or CSV

📚 **History Management**
- View all past experiments
- Filter by participant ID
- Compare multiple experiments side-by-side
- Visualize performance trends
- Bulk export capabilities

## Architecture

```
fyp/web_gui/
├── app.py                 # Flask web server with API endpoints
├── database.py            # SQLite database layer for experiment storage
├── analysis_pipeline.py   # Automated data processing and visualization
├── run_server.py          # Server startup script
├── templates/             # HTML templates
│   ├── index.html         # Launch screen
│   ├── results.html       # Results display
│   └── history.html       # Experiment history
└── static/                # Frontend assets
    ├── styles.css         # UI styling
    ├── app.js             # Main JavaScript
    ├── results.js         # Results page logic
    └── history.js         # History page logic
```

## Installation

1. **Install dependencies**:
   ```bash
   cd fyp
   pip install -r requirements.txt
   ```

2. **Verify installation**:
   ```bash
   python3 -c "import flask; print('Flask installed')"
   ```

## Usage

### Starting the Server

**Method 1: Automated startup (Recommended)**
```bash
cd fyp/web_gui
python3 run_server.py
```
This will:
- Check if port 5000 is available
- Start the Flask server
- Automatically open your browser to http://localhost:5000

**Method 2: Manual startup**
```bash
cd fyp/web_gui
python3 app.py
```
Then manually open http://localhost:5000 in your browser.

### Running an Experiment

1. **Launch Screen**
   - Enter a unique Participant ID (e.g., "P001", "TEST_USER")
   - Toggle haptic guidance on/off
   - (Optional) Expand "Advanced Parameters" to adjust haptic stiffness
   - Click "Start Experiment"

2. **Experiment Execution**
   - A Pygame window will open showing the 3D polyline path
   - Follow the path using the haptic device or mouse
   - Complete the task by reaching the orange endpoint
   - The window will close automatically when finished

3. **View Results**
   - You'll be redirected to the results page automatically
   - Review metrics, visualizations, and detailed statistics
   - Export PDF report or CSV data

### Viewing History

1. Navigate to the "History" tab
2. Browse all past experiments in a sortable table
3. Use the filter to show only specific participants
4. Select multiple experiments and click "Compare Selected"
5. View side-by-side comparison charts and metrics

### Exporting Data

**PDF Report** (Single Experiment):
- Click "Export PDF Report" on the results page
- Contains experiment details, metrics, and visualizations

**CSV Export** (Multiple Experiments):
- Click "Export CSV" on results or history page
- Exports all experiments for the current participant

**Comparison Export**:
- Select experiments in the history view
- Click "Compare Selected"
- Export comparison visualizations and data

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/experiment/start` | POST | Start a new experiment |
| `/api/experiment/status/{id}` | GET | Check experiment status |
| `/api/experiment/results/{id}` | GET | Get experiment results |
| `/api/experiments/history` | GET | List all experiments |
| `/api/experiments/compare` | GET | Compare multiple experiments |
| `/api/export/pdf/{id}` | GET | Download PDF report |
| `/api/export/csv` | GET | Download CSV data |
| `/api/visualization/{id}/{filename}` | GET | Serve visualization images |

## Data Storage

### Database
- **Location**: `fyp/web_gui/experiments.db`
- **Type**: SQLite
- **Tables**:
  - `experiments`: Experiment metadata (participant, timestamp, parameters, status)
  - `metrics`: Computed performance metrics (jitter, lateral error, path efficiency)

### Raw Data
- **Location**: `polyline_data/experiments/`
- **Format**: JSON files with complete tick-by-tick experiment data
- **Naming**: `experiment_{id}_{timestamp}.json`

### Processed Outputs
- **Location**: `outputs/experiments/{experiment_id}/`
- **Contents**:
  - `trajectory_3d.png`: 3D trajectory visualization
  - `jitter_analysis.png`: Jitter over time plot
  - `filtered_data.json`: Processed data with metrics

## Configuration

### Experiment Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `k_xy` | 0.06 | 0.01 - 0.20 | XY plane haptic stiffness |
| `k_z` | 0.15 | 0.05 - 0.30 | Z-axis haptic stiffness |
| `haptic_enabled` | true | true/false | Enable haptic guidance |

### Server Configuration

Edit [app.py](app.py) to change:
- **Port**: Default 5000 (line: `app.run(port=5000)`)
- **Host**: Default `0.0.0.0` (accessible from network)
- **Debug mode**: Set `debug=False` for production

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
lsof -ti:5000

# Kill the process
kill -9 <PID>
```

### Haptic Device Not Found
- The experiment will automatically fall back to visual-only mode
- Use mouse to trace the path instead
- Check that OpenHaptics SDK is installed and device is connected

### Database Errors
```bash
# Reset database (WARNING: Deletes all experiments)
rm fyp/web_gui/experiments.db
python3 -c "from database import init_database; init_database()"
```

### Missing Visualizations
- Ensure matplotlib is installed: `pip install matplotlib`
- Check that `outputs/experiments/` directory exists and is writable
- Review server logs for analysis pipeline errors

## Development

### Running in Debug Mode
```python
# In app.py, set:
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Adding New Metrics
1. Update `analysis_pipeline.py` to compute new metric
2. Add column to `metrics` table in `database.py`
3. Update `save_metrics()` to include new field
4. Modify frontend templates to display new metric

### Customizing UI
- Edit `static/styles.css` for styling changes
- Modify templates in `templates/` for layout changes
- Update JavaScript in `static/` for behavior changes

## Dependencies

- **Flask 3.0.2**: Web framework
- **Flask-CORS 4.0.0**: Cross-origin resource sharing
- **scipy 1.11.4**: Signal processing (Butterworth filter)
- **reportlab 4.1.0**: PDF generation
- **numpy, matplotlib**: Data processing and visualization
- **pygame, pyOpenHaptics**: Experiment execution (inherited from parent)

## Credits

Built as part of the CDE4301 Final Year Project on haptic guidance research.

## License

See parent project README for licensing information.
