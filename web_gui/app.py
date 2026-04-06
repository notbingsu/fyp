"""
Haptic experiment server.

- WebSocket server (ws://localhost:5001) — Unity connects here to start/stop sessions.
- REST API (http://localhost:5000)       — query results, history, and export CSV.
"""
import asyncio
import json
import sys
import threading
import time
import csv
import argparse
from datetime import datetime
from io import StringIO, BytesIO
from pathlib import Path

import websockets
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# Add parent directory so experiment_runner can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    create_experiment, update_experiment_status, save_metrics,
    get_experiment, get_experiment_by_run_id,
    get_experiment_with_metrics, get_experiment_with_metrics_by_run_id,
    get_all_experiments, get_experiments_by_ids,
    get_experiments_by_participant_scenario,
    get_participant_statistics, get_run_id,
)
from analysis_pipeline import analyze_experiment, generate_comparison_visualization
from experiment_runner import run_experiment, WAYPOINTS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "experiments"
OUTPUT_DIR = BASE_DIR / "outputs" / "experiments"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Flask REST API
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


@app.route('/api/experiment/status/<run_id>', methods=['GET'])
def get_experiment_status(run_id):
    experiment = get_experiment_by_run_id(run_id)
    if not experiment:
        return jsonify({'error': 'Experiment not found'}), 404
    return jsonify({
        'run_id': run_id,
        'status': experiment['status'],
        'participant_id': experiment['participant_id'],
        'scenario': experiment['scenario'],
    })


@app.route('/api/experiment/results/<run_id>', methods=['GET'])
def get_experiment_results(run_id):
    experiment = get_experiment_with_metrics_by_run_id(run_id)
    if not experiment:
        return jsonify({'error': 'Experiment not found'}), 404
    if experiment['status'] != 'completed':
        return jsonify({'error': 'Experiment not yet completed'}), 400

    exp_id = experiment['id']
    visualizations = {
        'trajectory_3d': f'/api/visualization/{run_id}/trajectory_3d.png',
        'jitter_analysis': f'/api/visualization/{run_id}/jitter_analysis.png',
    }
    return jsonify({
        'experiment': {
            'run_id': run_id,
            'participant_id': experiment['participant_id'],
            'scenario': experiment['scenario'],
            'timestamp': experiment['timestamp'],
            'haptic_enabled': bool(experiment['haptic_enabled']),
            'k_xy': experiment['k_xy'],
            'k_z': experiment['k_z'],
        },
        'metrics': {
            'path_efficiency': experiment.get('path_efficiency'),
            'total_duration': experiment.get('total_duration'),
            'jitter_rms': experiment.get('jitter_rms'),
            'jitter_mean': experiment.get('jitter_mean'),
            'jitter_std': experiment.get('jitter_std'),
            'lateral_error_rms': experiment.get('lateral_error_rms'),
            'lateral_error_mean': experiment.get('lateral_error_mean'),
            'lateral_error_std': experiment.get('lateral_error_std'),
            'ideal_path_length': experiment.get('ideal_path_length'),
            'actual_path_length': experiment.get('actual_path_length'),
            'excess_path_length': experiment.get('excess_path_length'),
        },
        'visualizations': visualizations,
    })


@app.route('/api/visualization/<run_id>/<filename>')
def get_visualization(run_id, filename):
    viz_path = OUTPUT_DIR / run_id / filename
    if not viz_path.exists():
        return jsonify({'error': 'Visualization not found'}), 404
    return send_file(viz_path, mimetype='image/png')


@app.route('/api/visualization/comparison/<filename>')
def get_comparison_visualization(filename):
    viz_path = OUTPUT_DIR / filename
    if not viz_path.exists():
        return jsonify({'error': 'Visualization not found'}), 404
    return send_file(viz_path, mimetype='image/png')


@app.route('/api/experiments/history', methods=['GET'])
def get_experiments_history():
    participant_id = request.args.get('participant_id')
    scenario = request.args.get('scenario')
    experiments = get_all_experiments(participant_id, scenario)
    return jsonify({'experiments': experiments, 'count': len(experiments)})


@app.route('/api/experiments/progress', methods=['GET'])
def get_participant_progress():
    """Return per-attempt metrics for a participant+scenario (for plotting improvement)."""
    participant_id = request.args.get('participant_id')
    scenario = request.args.get('scenario')
    if not participant_id or not scenario:
        return jsonify({'error': 'participant_id and scenario are required'}), 400
    rows = get_experiments_by_participant_scenario(participant_id, scenario)
    return jsonify({'attempts': rows, 'count': len(rows)})


@app.route('/api/experiments/compare', methods=['GET'])
def compare_experiments():
    ids_str = request.args.get('ids', '')
    experiment_ids = [int(i.strip()) for i in ids_str.split(',') if i.strip()]
    if not experiment_ids:
        return jsonify({'error': 'No experiment IDs provided'}), 400
    experiments = get_experiments_by_ids(experiment_ids)
    if not experiments:
        return jsonify({'error': 'No experiments found'}), 404
    comparison_path = OUTPUT_DIR / f"comparison_{'_'.join(map(str, experiment_ids))}.png"
    generate_comparison_visualization(experiment_ids, experiments, comparison_path)
    return jsonify({
        'experiments': experiments,
        'comparison_chart': f"/api/visualization/comparison/comparison_{'_'.join(map(str, experiment_ids))}.png",
    })


@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    participant_id = request.args.get('participant_id')
    scenario = request.args.get('scenario')
    experiments = get_experiments_by_ids(
        [exp['id'] for exp in get_all_experiments(participant_id, scenario)]
    )
    if not experiments:
        return jsonify({'error': 'No experiments found'}), 404

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Run ID', 'Participant ID', 'Scenario', 'Timestamp', 'Haptics Enabled',
        'K_XY', 'K_Z', 'Duration (s)', 'Path Efficiency (%)',
        'RMS Jitter (mm)', 'RMS Lateral Error (mm)',
        'Ideal Path (mm)', 'Actual Path (mm)', 'Excess Path (mm)',
    ])
    for exp in experiments:
        writer.writerow([
            exp.get('run_id', ''),
            exp['participant_id'],
            exp.get('scenario', ''),
            exp['timestamp'],
            'Yes' if exp['haptic_enabled'] else 'No',
            exp['k_xy'],
            exp['k_z'],
            exp.get('total_duration', ''),
            exp.get('path_efficiency', ''),
            exp.get('jitter_rms', ''),
            exp.get('lateral_error_rms', ''),
            exp.get('ideal_path_length', ''),
            exp.get('actual_path_length', ''),
            exp.get('excess_path_length', ''),
        ])

    output.seek(0)
    label = f"{participant_id or 'all'}_{scenario or 'all'}_{datetime.now().strftime('%Y%m%d')}"
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name=f'experiments_{label}.csv',
        mimetype='text/csv',
    )


def start_flask(port: int):
    """Start Flask REST API in a daemon thread."""
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


# ---------------------------------------------------------------------------
# WebSocket server — Unity communication
# ---------------------------------------------------------------------------

# Tracks the active experiment per WebSocket connection:
# { websocket: { 'experiment_id': int, 'stop_event': Event, 'thread': Thread } }
_active_sessions: dict = {}


def _run_and_analyse(experiment_id: int, run_id: str, scenario: str,
                     participant_id: str, haptic_enabled: bool,
                     k_xy: float, k_z: float,
                     stop_event: threading.Event,
                     result_container: list):
    """Worker run in a thread: execute experiment then analyse."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = str(DATA_DIR / f"{run_id}.json")

        update_experiment_status(experiment_id, 'running')

        saved_path = run_experiment(
            scenario=scenario,
            participant_id=participant_id,
            haptic_enabled=haptic_enabled,
            stop_event=stop_event,
            output_path=output_path,
        )

        # Read back duration from saved JSON
        import json as _json
        with open(saved_path) as f:
            raw = _json.load(f)
        duration = raw['metadata']['total_duration_seconds']

        update_experiment_status(experiment_id, 'completed',
                                 duration=duration, raw_data_path=saved_path)

        exp_output_dir = OUTPUT_DIR / run_id
        metrics = analyze_experiment(saved_path, exp_output_dir)
        save_metrics(experiment_id, metrics)

        result_container.append({'status': 'completed', 'metrics': metrics})

    except Exception as exc:
        update_experiment_status(experiment_id, 'failed')
        result_container.append({'status': 'failed', 'error': str(exc)})


async def ws_handler(websocket):
    """Handle a Unity WebSocket connection.

    Expected message flow:
        Unity → {"action":"start","participant":"p1","scenario":"Test1",
                  "haptic":true,"k_xy":0.06,"k_z":0.15}
        Server → {"status":"started","run_id":"p1_Test1_20260330_120000"}
        Unity → {"action":"stop"}
        Server → {"status":"completed","run_id":"...","metrics":{...}}
                 OR {"status":"failed","error":"..."}
    """
    session = None
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({'status': 'error', 'error': 'Invalid JSON'}))
                continue

            action = msg.get('action')

            if action == 'start':
                if session is not None:
                    await websocket.send(json.dumps({'status': 'error', 'error': 'Session already active'}))
                    continue

                participant_id = str(msg.get('participant', '')).strip()
                scenario = str(msg.get('scenario', '')).strip()
                haptic_enabled = bool(msg.get('haptic', True))
                k_xy = float(msg.get('k_xy', 0.06))
                k_z = float(msg.get('k_z', 0.15))

                # Validate
                errors = []
                if not participant_id:
                    errors.append('participant is required')
                if scenario not in WAYPOINTS:
                    errors.append(f"scenario must be one of {list(WAYPOINTS.keys())}")
                if not (0.01 <= k_xy <= 0.5):
                    errors.append('k_xy must be between 0.01 and 0.5')
                if not (0.05 <= k_z <= 0.5):
                    errors.append('k_z must be between 0.05 and 0.5')

                if errors:
                    await websocket.send(json.dumps({'status': 'error', 'error': '; '.join(errors)}))
                    continue

                experiment_id = create_experiment(participant_id, scenario, haptic_enabled, k_xy, k_z)
                run_id = get_run_id(experiment_id)

                stop_event = threading.Event()
                result_container = []
                thread = threading.Thread(
                    target=_run_and_analyse,
                    args=(experiment_id, run_id, scenario, participant_id,
                          haptic_enabled, k_xy, k_z, stop_event, result_container),
                    daemon=True,
                )
                thread.start()

                session = {
                    'experiment_id': experiment_id,
                    'run_id': run_id,
                    'stop_event': stop_event,
                    'thread': thread,
                    'result_container': result_container,
                }
                _active_sessions[id(websocket)] = session

                await websocket.send(json.dumps({'status': 'started', 'run_id': run_id}))

            elif action == 'stop':
                if session is None:
                    await websocket.send(json.dumps({'status': 'error', 'error': 'No active session'}))
                    continue

                session['stop_event'].set()
                session['thread'].join(timeout=60)

                result = session['result_container'][0] if session['result_container'] else {'status': 'failed', 'error': 'No result'}
                response = {'run_id': session['run_id'], **result}
                await websocket.send(json.dumps(response))
                session = None

            else:
                await websocket.send(json.dumps({'status': 'error', 'error': f"Unknown action '{action}'"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Clean up if connection drops mid-session
        if session is not None:
            session['stop_event'].set()
        _active_sessions.pop(id(websocket), None)


async def start_websocket_server(ws_port: int):
    async with websockets.serve(ws_handler, '0.0.0.0', ws_port):
        await asyncio.get_running_loop().create_future()  # run forever


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(rest_port: int = 5000, ws_port: int = 5001):
    # Flask in a background daemon thread
    flask_thread = threading.Thread(
        target=start_flask, args=(rest_port,), daemon=True
    )
    flask_thread.start()

    print("=" * 50)
    print("Haptic Experiment Server")
    print("=" * 50)
    print(f"REST API:  http://localhost:{rest_port}")
    print(f"WebSocket: ws://localhost:{ws_port}")
    print()
    print(f"Available scenarios: {list(WAYPOINTS.keys())}")
    print()
    print("Connect Unity to ws://localhost:{ws_port}")
    print("Press Ctrl+C to stop.")
    print("=" * 50)

    asyncio.run(start_websocket_server(ws_port))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Haptic Experiment Server')
    parser.add_argument('--rest-port', type=int, default=5000)
    parser.add_argument('--ws-port', type=int, default=5001)
    args = parser.parse_args()
    main(rest_port=args.rest_port, ws_port=args.ws_port)
