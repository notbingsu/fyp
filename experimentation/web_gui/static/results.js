// Results page functionality

document.addEventListener('DOMContentLoaded', async () => {
    const loadingState = document.getElementById('loading-state');
    const resultsContent = document.getElementById('results-content');
    const errorState = document.getElementById('error-state');
    const errorMessage = document.getElementById('error-message');

    try {
        // Fetch experiment results
        const response = await fetch(`${API_BASE}/experiment/results/${experimentId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load results');
        }

        // Populate experiment info
        document.getElementById('exp-id').textContent = data.experiment.id;
        document.getElementById('participant-id').textContent = data.experiment.participant_id;
        document.getElementById('exp-date').textContent = formatDate(data.experiment.timestamp);
        document.getElementById('haptics-status').textContent = data.experiment.haptic_enabled ? 'Enabled' : 'Disabled';

        // Populate metrics
        const metrics = data.metrics;
        document.getElementById('path-efficiency').textContent = formatNumber(metrics.path_efficiency) + '%';
        document.getElementById('duration').textContent = formatNumber(metrics.total_duration);
        document.getElementById('jitter-rms').textContent = formatNumber(metrics.jitter_rms);
        document.getElementById('lateral-error').textContent = formatNumber(metrics.lateral_error_rms);

        // Detailed metrics
        document.getElementById('ideal-path').textContent = formatNumber(metrics.ideal_path_length) + ' mm';
        document.getElementById('actual-path').textContent = formatNumber(metrics.actual_path_length) + ' mm';
        document.getElementById('excess-path').textContent = formatNumber(metrics.excess_path_length) + ' mm';
        document.getElementById('jitter-stats').textContent =
            `${formatNumber(metrics.jitter_mean)} ± ${formatNumber(metrics.jitter_std)} mm`;
        document.getElementById('lateral-stats').textContent =
            `${formatNumber(metrics.lateral_error_mean)} ± ${formatNumber(metrics.lateral_error_std)} mm`;

        // Load visualizations
        document.getElementById('trajectory-viz').src = data.visualizations.trajectory_3d;
        document.getElementById('jitter-viz').src = data.visualizations.jitter_analysis;

        // Show results
        loadingState.style.display = 'none';
        resultsContent.style.display = 'block';

    } catch (error) {
        console.error('Error loading results:', error);
        errorMessage.textContent = error.message;
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
    }
});

// Export PDF button
document.getElementById('export-pdf')?.addEventListener('click', () => {
    window.open(`${API_BASE}/export/pdf/${experimentId}`, '_blank');
});

// Export CSV button
document.getElementById('export-csv')?.addEventListener('click', () => {
    const participantId = document.getElementById('participant-id').textContent;
    window.open(`${API_BASE}/export/csv?participant_id=${participantId}`, '_blank');
});
