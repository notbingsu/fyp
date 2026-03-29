// History page functionality

let allExperiments = [];
let selectedExperiments = new Set();

document.addEventListener('DOMContentLoaded', async () => {
    await loadExperiments();

    // Set up event listeners
    document.getElementById('filter-btn').addEventListener('click', filterExperiments);
    document.getElementById('clear-filter-btn').addEventListener('click', clearFilter);
    document.getElementById('select-all').addEventListener('change', toggleSelectAll);
    document.getElementById('compare-btn').addEventListener('click', compareSelected);
    document.getElementById('close-comparison')?.addEventListener('click', closeComparison);
});

async function loadExperiments(participantId = null) {
    const loadingState = document.getElementById('loading-state');
    const tableContainer = document.getElementById('experiments-table-container');
    const emptyState = document.getElementById('empty-state');

    try {
        let url = `${API_BASE}/experiments/history`;
        if (participantId) {
            url += `?participant_id=${participantId}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load experiments');
        }

        allExperiments = data.experiments;

        loadingState.style.display = 'none';

        if (allExperiments.length === 0) {
            emptyState.style.display = 'block';
            tableContainer.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            tableContainer.style.display = 'block';
            renderExperimentsTable();
        }

    } catch (error) {
        console.error('Error loading experiments:', error);
        loadingState.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

function renderExperimentsTable() {
    const tbody = document.getElementById('experiments-tbody');
    tbody.innerHTML = '';

    allExperiments.forEach(exp => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" class="exp-checkbox" data-id="${exp.id}"></td>
            <td>${exp.id}</td>
            <td>${exp.participant_id}</td>
            <td>${formatDate(exp.timestamp)}</td>
            <td>${exp.haptic_enabled ? '✓' : '✗'}</td>
            <td>${formatNumber(exp.total_duration)}</td>
            <td>${formatNumber(exp.path_efficiency)}</td>
            <td>${formatNumber(exp.jitter_rms)}</td>
            <td>${formatNumber(exp.lateral_error_rms)}</td>
            <td>
                <a href="/results/${exp.id}" class="btn-small btn-view">View</a>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Add checkbox listeners
    document.querySelectorAll('.exp-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', handleCheckboxChange);
    });
}

function handleCheckboxChange(e) {
    const id = parseInt(e.target.dataset.id);

    if (e.target.checked) {
        selectedExperiments.add(id);
    } else {
        selectedExperiments.delete(id);
        document.getElementById('select-all').checked = false;
    }

    updateCompareButton();
}

function updateCompareButton() {
    const count = selectedExperiments.size;
    document.getElementById('selected-count').textContent = count;
    document.getElementById('compare-btn').disabled = count < 2;
}

function toggleSelectAll(e) {
    const checkboxes = document.querySelectorAll('.exp-checkbox');

    if (e.target.checked) {
        checkboxes.forEach(cb => {
            cb.checked = true;
            selectedExperiments.add(parseInt(cb.dataset.id));
        });
    } else {
        checkboxes.forEach(cb => {
            cb.checked = false;
        });
        selectedExperiments.clear();
    }

    updateCompareButton();
}

function filterExperiments() {
    const participantId = document.getElementById('participant-filter').value.trim();
    if (participantId) {
        loadExperiments(participantId);
    }
}

function clearFilter() {
    document.getElementById('participant-filter').value = '';
    loadExperiments();
}

async function compareSelected() {
    if (selectedExperiments.size < 2) {
        alert('Please select at least 2 experiments to compare');
        return;
    }

    const comparisonSection = document.getElementById('comparison-section');
    comparisonSection.style.display = 'block';
    comparisonSection.scrollIntoView({ behavior: 'smooth' });

    try {
        const ids = Array.from(selectedExperiments).join(',');
        const response = await fetch(`${API_BASE}/experiments/compare?ids=${ids}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to compare experiments');
        }

        // Update comparison chart
        document.getElementById('comparison-chart').src = data.comparison_chart;

        // Update comparison table
        renderComparisonTable(data.experiments);

    } catch (error) {
        console.error('Error comparing experiments:', error);
        alert(`Error: ${error.message}`);
    }
}

function renderComparisonTable(experiments) {
    // Update header with experiment IDs
    experiments.forEach((exp, index) => {
        const header = document.getElementById(`comp-exp-${index + 1}`);
        if (header) {
            header.textContent = `Exp ${exp.id}`;
            header.style.display = 'table-cell';
        }
    });

    // Hide unused columns
    for (let i = experiments.length + 1; i <= 4; i++) {
        const header = document.getElementById(`comp-exp-${i}`);
        if (header) {
            header.style.display = 'none';
        }
    }

    // Populate rows
    const tbody = document.getElementById('comparison-tbody');
    tbody.innerHTML = '';

    const metrics = [
        { label: 'Participant ID', key: 'participant_id', format: v => v },
        { label: 'Haptics', key: 'haptic_enabled', format: v => v ? 'Yes' : 'No' },
        { label: 'Path Efficiency (%)', key: 'path_efficiency', format: formatNumber },
        { label: 'Duration (s)', key: 'total_duration', format: formatNumber },
        { label: 'RMS Jitter (mm)', key: 'jitter_rms', format: formatNumber },
        { label: 'RMS Lateral Error (mm)', key: 'lateral_error_rms', format: formatNumber },
        { label: 'Ideal Path (mm)', key: 'ideal_path_length', format: formatNumber },
        { label: 'Actual Path (mm)', key: 'actual_path_length', format: formatNumber },
        { label: 'Excess Path (mm)', key: 'excess_path_length', format: formatNumber }
    ];

    metrics.forEach(metric => {
        const row = document.createElement('tr');
        let html = `<td><strong>${metric.label}</strong></td>`;

        experiments.forEach((exp, index) => {
            html += `<td class="comparison-exp">${metric.format(exp[metric.key])}</td>`;
        });

        // Hide unused columns
        for (let i = experiments.length; i < 4; i++) {
            html += `<td class="comparison-exp" style="display: none;"></td>`;
        }

        row.innerHTML = html;
        tbody.appendChild(row);
    });
}

function closeComparison() {
    document.getElementById('comparison-section').style.display = 'none';
}
