"""Flask web application for haptic experiment GUI."""
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import subprocess
import json
import time
import threading
import argparse
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import csv
from io import StringIO, BytesIO

from database import (
    create_experiment, update_experiment_status, save_metrics,
    get_experiment, get_experiment_with_metrics, get_all_experiments,
    get_experiments_by_ids, get_participant_statistics
)
from analysis_pipeline import analyze_experiment, generate_comparison_visualization

app = Flask(__name__)
CORS(app)

# Paths
BASE_DIR = Path(__file__).parent.parent
MOUSE_DEMO_DIR = BASE_DIR / "mouse_demo"
POLYLINE_TRACKER = MOUSE_DEMO_DIR / "polyline_tracker_3d.py"
DATA_DIR = BASE_DIR.parent / "polyline_data" / "experiments"
OUTPUT_DIR = BASE_DIR.parent / "outputs" / "experiments"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Track running experiments
active_experiments = {}


def run_experiment_subprocess(experiment_id: int, participant_id: str, 
                              haptic_enabled: bool, k_xy: float, k_z: float):
    """Run experiment in subprocess and update database when complete."""
    try:
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"experiment_{experiment_id}_{timestamp}.json"
        output_path = DATA_DIR / output_filename
        
        # Build command
        cmd = [
            "python3",
            str(POLYLINE_TRACKER),
            "--participant-id", participant_id,
            "--k-xy", str(k_xy),
            "--k-z", str(k_z),
            "--output-file", str(output_path)
        ]
        
        if not haptic_enabled:
            cmd.append("--no-haptics")
        
        # Update status to running
        update_experiment_status(experiment_id, "running")
        
        # Run experiment
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(MOUSE_DEMO_DIR)
        )
        
        active_experiments[experiment_id] = {
            'process': process,
            'status': 'running',
            'start_time': time.time()
        }
        
        # Wait for completion
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Load experiment data to get duration
            with open(output_path, 'r') as f:
                exp_data = json.load(f)
                duration = exp_data['metadata']['total_duration_seconds']
            
            # Update database
            update_experiment_status(
                experiment_id, 
                "completed", 
                duration=duration,
                raw_data_path=str(output_path)
            )
            
            # Run analysis
            exp_output_dir = OUTPUT_DIR / str(experiment_id)
            metrics = analyze_experiment(str(output_path), exp_output_dir)
            save_metrics(experiment_id, metrics)
            
            active_experiments[experiment_id]['status'] = 'completed'
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            print(f"Experiment {experiment_id} failed: {error_msg}")
            update_experiment_status(experiment_id, "failed")
            active_experiments[experiment_id]['status'] = 'failed'
            
    except Exception as e:
        print(f"Error running experiment {experiment_id}: {str(e)}")
        update_experiment_status(experiment_id, "failed")
        if experiment_id in active_experiments:
            active_experiments[experiment_id]['status'] = 'failed'


@app.route('/')
def index():
    """Main launch screen."""
    return render_template('index.html')


@app.route('/results/<int:experiment_id>')
def results(experiment_id):
    """Results screen for a completed experiment."""
    return render_template('results.html', experiment_id=experiment_id)


@app.route('/history')
def history():
    """Experiment history dashboard."""
    return render_template('history.html')


@app.route('/api/experiment/start', methods=['POST'])
def start_experiment():
    """Start a new experiment."""
    try:
        data = request.json
        
        # Validate inputs
        participant_id = data.get('participant_id', '').strip()
        if not participant_id:
            return jsonify({'error': 'Participant ID is required'}), 400
        
        haptic_enabled = data.get('haptic_enabled', True)
        k_xy = float(data.get('k_xy', 0.06))
        k_z = float(data.get('k_z', 0.15))
        
        # Validate parameters
        if not (0.01 <= k_xy <= 0.5):
            return jsonify({'error': 'k_xy must be between 0.01 and 0.5'}), 400
        if not (0.05 <= k_z <= 0.5):
            return jsonify({'error': 'k_z must be between 0.05 and 0.5'}), 400
        
        # Create experiment record
        experiment_id = create_experiment(participant_id, haptic_enabled, k_xy, k_z)
        
        # Start experiment in background thread
        thread = threading.Thread(
            target=run_experiment_subprocess,
            args=(experiment_id, participant_id, haptic_enabled, k_xy, k_z)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'experiment_id': experiment_id,
            'status': 'started',
            'message': 'Experiment started successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiment/status/<int:experiment_id>', methods=['GET'])
def get_experiment_status(experiment_id):
    """Check experiment status."""
    try:
        experiment = get_experiment(experiment_id)
        
        if not experiment:
            return jsonify({'error': 'Experiment not found'}), 404
        
        # Check active experiments for real-time status
        if experiment_id in active_experiments:
            status = active_experiments[experiment_id]['status']
        else:
            status = experiment['status']
        
        return jsonify({
            'experiment_id': experiment_id,
            'status': status,
            'participant_id': experiment['participant_id']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiment/results/<int:experiment_id>', methods=['GET'])
def get_experiment_results(experiment_id):
    """Get experiment results with metrics."""
    try:
        experiment = get_experiment_with_metrics(experiment_id)
        
        if not experiment:
            return jsonify({'error': 'Experiment not found'}), 404
        
        if experiment['status'] != 'completed':
            return jsonify({'error': 'Experiment not yet completed'}), 400
        
        # Build visualization URLs
        viz_dir = OUTPUT_DIR / str(experiment_id)
        visualizations = {
            'trajectory_3d': f'/api/visualization/{experiment_id}/trajectory_3d.png',
            'jitter_analysis': f'/api/visualization/{experiment_id}/jitter_analysis.png'
        }
        
        return jsonify({
            'experiment': {
                'id': experiment['id'],
                'participant_id': experiment['participant_id'],
                'timestamp': experiment['timestamp'],
                'haptic_enabled': bool(experiment['haptic_enabled']),
                'k_xy': experiment['k_xy'],
                'k_z': experiment['k_z']
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
                'excess_path_length': experiment.get('excess_path_length')
            },
            'visualizations': visualizations
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/visualization/<int:experiment_id>/<filename>')
def get_visualization(experiment_id, filename):
    """Serve visualization image."""
    try:
        viz_path = OUTPUT_DIR / str(experiment_id) / filename
        
        if not viz_path.exists():
            return jsonify({'error': 'Visualization not found'}), 404
        
        return send_file(viz_path, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiments/history', methods=['GET'])
def get_experiments_history():
    """Get all experiments, optionally filtered by participant."""
    try:
        participant_id = request.args.get('participant_id')
        experiments = get_all_experiments(participant_id)
        
        return jsonify({
            'experiments': experiments,
            'count': len(experiments)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiments/compare', methods=['GET'])
def compare_experiments():
    """Compare multiple experiments."""
    try:
        ids_str = request.args.get('ids', '')
        experiment_ids = [int(id.strip()) for id in ids_str.split(',') if id.strip()]
        
        if not experiment_ids:
            return jsonify({'error': 'No experiment IDs provided'}), 400
        
        experiments = get_experiments_by_ids(experiment_ids)
        
        if not experiments:
            return jsonify({'error': 'No experiments found'}), 404
        
        # Generate comparison visualization
        comparison_path = OUTPUT_DIR / f"comparison_{'_'.join(map(str, experiment_ids))}.png"
        generate_comparison_visualization(experiment_ids, experiments, comparison_path)
        
        return jsonify({
            'experiments': experiments,
            'comparison_chart': f"/api/visualization/comparison/{'_'.join(map(str, experiment_ids))}.png"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/visualization/comparison/<filename>')
def get_comparison_visualization(filename):
    """Serve comparison visualization."""
    try:
        viz_path = OUTPUT_DIR / filename
        
        if not viz_path.exists():
            return jsonify({'error': 'Visualization not found'}), 404
        
        return send_file(viz_path, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/pdf/<int:experiment_id>', methods=['GET'])
def export_pdf(experiment_id):
    """Generate and download PDF report for an experiment."""
    try:
        experiment = get_experiment_with_metrics(experiment_id)
        
        if not experiment:
            return jsonify({'error': 'Experiment not found'}), 404
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph('Experiment Report', title_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Experiment details
        story.append(Paragraph('<b>Experiment Details</b>', styles['Heading2']))
        details_data = [
            ['Experiment ID:', str(experiment['id'])],
            ['Participant ID:', experiment['participant_id']],
            ['Date/Time:', experiment['timestamp']],
            ['Haptics Enabled:', 'Yes' if experiment['haptic_enabled'] else 'No'],
            ['K_XY Gain:', f"{experiment['k_xy']:.3f}"],
            ['K_Z Gain:', f"{experiment['k_z']:.3f}"]
        ]
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(details_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Metrics
        story.append(Paragraph('<b>Performance Metrics</b>', styles['Heading2']))
        metrics_data = [
            ['Metric', 'Value'],
            ['Path Efficiency', f"{experiment.get('path_efficiency', 0):.2f}%"],
            ['Task Duration', f"{experiment.get('total_duration', 0):.2f} seconds"],
            ['RMS Jitter', f"{experiment.get('jitter_rms', 0):.2f} mm"],
            ['RMS Lateral Error', f"{experiment.get('lateral_error_rms', 0):.2f} mm"],
            ['Ideal Path Length', f"{experiment.get('ideal_path_length', 0):.2f} mm"],
            ['Actual Path Length', f"{experiment.get('actual_path_length', 0):.2f} mm"],
            ['Excess Path', f"{experiment.get('excess_path_length', 0):.2f} mm"]
        ]
        metrics_table = Table(metrics_data, colWidths=[3*inch, 3*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Visualizations
        viz_dir = OUTPUT_DIR / str(experiment_id)
        trajectory_path = viz_dir / 'trajectory_3d.png'
        jitter_path = viz_dir / 'jitter_analysis.png'
        
        if trajectory_path.exists():
            story.append(Paragraph('<b>3D Trajectory</b>', styles['Heading2']))
            img = Image(str(trajectory_path), width=6*inch, height=4*inch)
            story.append(img)
            story.append(Spacer(1, 0.2 * inch))
        
        if jitter_path.exists():
            story.append(PageBreak())
            story.append(Paragraph('<b>Jitter Analysis</b>', styles['Heading2']))
            img = Image(str(jitter_path), width=6*inch, height=3*inch)
            story.append(img)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'experiment_{experiment_id}_report.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export experiments data as CSV."""
    try:
        participant_id = request.args.get('participant_id')
        experiments = get_experiments_by_ids(
            [exp['id'] for exp in get_all_experiments(participant_id)]
        )
        
        if not experiments:
            return jsonify({'error': 'No experiments found'}), 404
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Experiment ID', 'Participant ID', 'Timestamp', 'Haptics Enabled',
            'K_XY', 'K_Z', 'Duration (s)', 'Path Efficiency (%)', 
            'RMS Jitter (mm)', 'RMS Lateral Error (mm)', 
            'Ideal Path (mm)', 'Actual Path (mm)', 'Excess Path (mm)'
        ])
        
        # Data rows
        for exp in experiments:
            writer.writerow([
                exp['id'],
                exp['participant_id'],
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
                exp.get('excess_path_length', '')
            ])
        
        # Prepare response
        output.seek(0)
        filename = f"experiments_{participant_id if participant_id else 'all'}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        return send_file(
            BytesIO(output.getvalue().encode('utf-8')),
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Haptic Experiment Web GUI')
    parser.add_argument('--port', type=int, default=5000, 
                       help='Port to run the server on (default: 5000)')
    args = parser.parse_args()
    
    print("Starting Haptic Experiment Web GUI...")
    print(f"Server running at http://localhost:{args.port}")
    app.run(debug=True, host='0.0.0.0', port=args.port)
