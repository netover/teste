/**
 * Main JavaScript file for the HWA Dashboard.
 * Handles API data fetching, UI rendering, and all interactivity
 * for the main dashboard page, including widgets and modal popups.
 */
document.addEventListener('DOMContentLoaded', () => {
    // DOM Element References
    const grid = document.getElementById('job-streams-grid');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');

    // A global-like variable to store the latest data from the API.
    // This allows different functions (like modal creation) to access the data
    // without needing to re-fetch it.
    let apiData = {};

    /**
     * Fetches the latest job stream data from the backend API.
     */
    const fetchData = async () => {
        // Show loading indicator only on the initial load.
        if (!grid.hasChildNodes()) loadingIndicator.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        try {
            const response = await fetch('/api/jobstreams');
            const data = await response.json();
            loadingIndicator.classList.add('hidden');
            if (data.error) throw new Error(data.error);
            renderData(data);
        } catch (error) {
            loadingIndicator.classList.add('hidden');
            showError(error.message);
        }
    };

    /**
     * Renders the data received from the API into the dashboard UI.
     * @param {object} data - The structured data object from the backend.
     */
    const renderData = (data) => {
        apiData = data; // Store the fresh data.

        // Update summary widgets with the latest counts.
        document.querySelector('#widget-running .widget-value').textContent = data.running_count || 0;
        document.querySelector('#widget-abend .widget-value').textContent = data.abend_count || 0;
        document.querySelector('#widget-total .widget-value').textContent = data.total_count || 0;

        // Render the main grid of all job streams.
        grid.innerHTML = '';
        const jobStreams = data.all_jobs || [];
        if (jobStreams.length === 0) {
            grid.innerHTML = '<p>No job streams found.</p>';
            return;
        }
        jobStreams.forEach(js => {
            const card = document.createElement('div');
            card.className = 'job-stream-card';
            const statusClass = getStatusClass(js.status);
            card.innerHTML = `<h3>${js.jobStreamName || 'N/A'}</h3><p><strong>Workstation:</strong> ${js.workstationName || 'N/A'}</p><p><strong>Status:</strong> <span class="status ${statusClass}">${js.status || 'N/A'}</span></p><p><strong>Start Time:</strong> ${js.startTime ? new Date(js.startTime).toLocaleString() : 'N/A'}</p>`;
            grid.appendChild(card);
        });
    };

    /**
     * Determines the appropriate CSS class for a given job status.
     * @param {string} status - The job status string from the API.
     * @returns {string} The CSS class name.
     */
    const getStatusClass = (status) => {
        if (!status) return 'status-unknown';
        const s = status.toLowerCase();
        if (s.includes('succ')) return 'status-success';
        if (s.includes('error') || s.includes('abend')) return 'status-error';
        if (s.includes('exec')) return 'status-running';
        if (s.includes('pend')) return 'status-pending';
        return 'status-unknown';
    };

    /**
     * Displays an error message in the designated error display area.
     * @param {string} message - The error message to display.
     */
    const showError = (message) => {
        errorDisplay.textContent = `Error: ${message}`;
        errorDisplay.classList.remove('hidden');
    };

    /**
     * Creates and displays a draggable modal window with a list of jobs.
     * @param {string} title - The title for the modal window.
     * @param {Array} jobList - The list of job objects to display.
     * @param {HTMLElement} originElement - The element that was clicked to open the modal, used for the animation origin.
     */
    const createJobListWindow = (title, jobList, originElement) => {
        // 1. Create Modal DOM Elements
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        const content = document.createElement('div');
        content.className = 'modal-content';
        const titleEl = document.createElement('h2');
        titleEl.className = 'modal-title';
        titleEl.textContent = title;
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close-btn';
        closeBtn.innerHTML = '&times;';
        const body = document.createElement('div');
        body.className = 'modal-body';
        let listHtml = '<ul>';
        if (jobList && jobList.length > 0) {
            jobList.forEach(job => {
                listHtml += `<li><strong>${job.jobStreamName}</strong> on ${job.workstationName}</li>`;
            });
        } else {
            listHtml += '<li>No jobs to display for this status.</li>';
        }
        listHtml += '</ul>';
        body.innerHTML = listHtml;
        content.appendChild(closeBtn);
        content.appendChild(titleEl);
        content.appendChild(body);
        overlay.appendChild(content);
        document.body.appendChild(overlay);

        // 2. Animate Modal Opening
        const originRect = originElement.getBoundingClientRect();
        content.style.left = `${originRect.left + (originRect.width / 2)}px`;
        content.style.top = `${originRect.top + (originRect.height / 2)}px`;
        content.style.transform = 'scale(0)';
        content.style.opacity = '0';

        requestAnimationFrame(() => {
            overlay.classList.add('visible');
            content.classList.add('animated-open');
        });

        // 3. Define Close Logic
        const closeModal = () => {
            content.classList.remove('animated-open');
            setTimeout(() => {
                if (document.body.contains(overlay)) document.body.removeChild(overlay);
            }, 300);
        };
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });

        // 4. Dragging Logic
        let isDragging = false;
        let offset = { x: 0, y: 0 };
        titleEl.style.cursor = 'grab';
        titleEl.addEventListener('mousedown', (e) => {
            isDragging = true;
            offset = { x: e.clientX - content.offsetLeft, y: e.clientY - content.offsetTop };
            titleEl.style.cursor = 'grabbing';
        });
        const onMouseMove = (e) => {
            if (!isDragging) return;
            content.style.transform = 'none';
            content.style.left = `${e.clientX - offset.x}px`;
            content.style.top = `${e.clientY - offset.y}px`;
        };
        const onMouseUp = () => {
            isDragging = false;
            titleEl.style.cursor = 'grab';
        };
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        // Cleanup dragging event listeners when the modal is closed to prevent memory leaks.
        const originalCloseModal = closeModal;
        closeBtn.onclick = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            originalCloseModal();
        };
    };

    // --- Initial Setup and Event Listeners ---

    // Add event listeners for the summary widgets to open modals.
    document.getElementById('widget-running').addEventListener('click', (e) => createJobListWindow('Running Jobs', apiData.jobs_running, e.currentTarget));
    document.getElementById('widget-abend').addEventListener('click', (e) => createJobListWindow('ABEND Jobs', apiData.jobs_abend, e.currentTarget));

    // Add event listener for the application shutdown button.
    const shutdownBtn = document.getElementById('shutdown-btn');
    if (shutdownBtn) {
        shutdownBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to shut down the application?')) {
                try {
                    await fetch('/shutdown', { method: 'POST' });
                    document.body.innerHTML = '<header><h1>Application Shut Down</h1></header><main><p>You can now close this browser tab.</p></main>';
                } catch (error) {
                    document.body.innerHTML = '<header><h1>Application Shut Down</h1></header><main><p>You can now close this browser tab.</p></main>';
                }
            }
        });
    }

    // Initial data fetch when the page loads, then set an interval to refresh it.
    fetchData();
    setInterval(fetchData, 30000);
});
