document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('job-streams-grid');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');

    const fetchData = async () => {
        // Show loading indicator only on first load
        if (!grid.hasChildNodes()) {
            loadingIndicator.classList.remove('hidden');
        }
        errorDisplay.classList.add('hidden');

        try {
            const response = await fetch('/api/jobstreams');
            const data = await response.json();

            loadingIndicator.classList.add('hidden');

            if (data.error) {
                throw new Error(data.error);
            }

            renderData(data);

        } catch (error) {
            loadingIndicator.classList.add('hidden');
            showError(error.message);
        }
    };

    const renderData = (jobStreams) => {
        // Clear previous data
        grid.innerHTML = '';

        if (jobStreams.length === 0) {
            grid.innerHTML = '<p>No job streams found.</p>';
            return;
        }

        jobStreams.forEach(js => {
            const card = document.createElement('div');
            card.className = 'job-stream-card';

            const statusClass = getStatusClass(js.status);

            card.innerHTML = `
                <h3>${js.jobStreamName || 'N/A'}</h3>
                <p><strong>Workstation:</strong> ${js.workstationName || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status ${statusClass}">${js.status || 'N/A'}</span></p>
                <p><strong>Start Time:</strong> ${js.startTime ? new Date(js.startTime).toLocaleString() : 'N/A'}</p>
            `;
            grid.appendChild(card);
        });
    };

    const getStatusClass = (status) => {
        if (!status) return '';
        const s = status.toLowerCase();
        // Basic status mapping
        if (s.includes('succ')) return 'status-success';
        if (s.includes('error') || s.includes('abend')) return 'status-error';
        if (s.includes('exec')) return 'status-running';
        if (s.includes('pend')) return 'status-pending';
        return 'status-unknown'; // A default fallback class
    };

    const showError = (message) => {
        errorDisplay.textContent = `Error: ${message}`;
        errorDisplay.classList.remove('hidden');
    };

    // Initial data fetch
    fetchData();

    // Refresh data every 30 seconds
    setInterval(fetchData, 30000);
});
