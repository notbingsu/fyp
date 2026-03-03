// Main application JavaScript
// Common functions and utilities

// API base URL
const API_BASE = window.location.origin + '/api';

// Utility: Format number to 2 decimal places
function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return Number(num).toFixed(2);
}

// Utility: Format timestamp to readable date
function formatDate(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Utility: Show/hide elements
function show(elementId) {
    document.getElementById(elementId).style.display = 'block';
}

function hide(elementId) {
    document.getElementById(elementId).style.display = 'none';
}

// Launch Screen Functionality
if (document.getElementById('experiment-form')) {
    const form = document.getElementById('experiment-form');
    const startBtn = document.getElementById('start-btn');
    const statusMessage = document.getElementById('status-message');
    const statusText = document.getElementById('status-text');

    // Slider value updates
    const kxySlider = document.getElementById('k-xy');
    const kxyValue = document.getElementById('k-xy-value');
    const kzSlider = document.getElementById('k-z');
    const kzValue = document.getElementById('k-z-value');

    if (kxySlider) {
        kxySlider.addEventListener('input', (e) => {
            kxyValue.textContent = e.target.value;
        });
    }

    if (kzSlider) {
        kzSlider.addEventListener('input', (e) => {
            kzValue.textContent = e.target.value;
        });
    }

    // Advanced options toggle
    const toggleAdvanced = document.getElementById('toggle-advanced');
    const advancedContent = document.getElementById('advanced-content');

    if (toggleAdvanced) {
        toggleAdvanced.addEventListener('click', () => {
            advancedContent.classList.toggle('expanded');
            const arrow = toggleAdvanced.querySelector('.arrow');
            arrow.textContent = advancedContent.classList.contains('expanded') ? '▲' : '▼';
        });
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const participantId = document.getElementById('participant-id').value.trim();
        const hapticEnabled = document.getElementById('haptic-enabled').checked;
        const kxy = parseFloat(kxySlider.value);
        const kz = parseFloat(kzSlider.value);

        if (!participantId) {
            alert('Please enter a participant ID');
            return;
        }

        // Disable form
        startBtn.disabled = true;
        form.style.opacity = '0.5';
        statusMessage.style.display = 'block';
        statusText.textContent = 'Starting experiment...';

        try {
            const response = await fetch(`${API_BASE}/experiment/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    participant_id: participantId,
                    haptic_enabled: hapticEnabled,
                    k_xy: kxy,
                    k_z: kz
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to start experiment');
            }

            const experimentId = data.experiment_id;
            statusText.textContent = 'Experiment running... Complete the task in the Pygame window.';

            // Poll for completion
            pollExperimentStatus(experimentId);

        } catch (error) {
            console.error('Error starting experiment:', error);
            statusText.textContent = `Error: ${error.message}`;
            statusMessage.classList.add('error');
            startBtn.disabled = false;
            form.style.opacity = '1';
        }
    });

    // Poll experiment status
    async function pollExperimentStatus(experimentId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE}/experiment/status/${experimentId}`);
                const data = await response.json();

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    statusText.textContent = 'Experiment complete! Redirecting to results...';
                    setTimeout(() => {
                        window.location.href = `/results/${experimentId}`;
                    }, 1500);
                } else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    statusText.textContent = 'Experiment failed. Please try again.';
                    statusMessage.classList.add('error');
                    startBtn.disabled = false;
                    form.style.opacity = '1';
                }
            } catch (error) {
                console.error('Error polling status:', error);
            }
        }, 2000); // Poll every 2 seconds
    }
}
