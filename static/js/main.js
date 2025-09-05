document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('job-streams-grid');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');
    let apiData = {}; // Store the latest API data globally

    const fetchData = async () => {
        if (!grid.hasChildNodes()) {
            loadingIndicator.classList.remove('hidden');
        }
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

    const renderData = (data) => {
        apiData = data;
        document.querySelector('#widget-running .widget-value').textContent = data.running_count || 0;
        document.querySelector('#widget-abend .widget-value').textContent = data.abend_count || 0;
        document.querySelector('#widget-total .widget-value').textContent = data.total_count || 0;

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
        if (s.includes('succ')) return 'status-success';
        if (s.includes('error') || s.includes('abend')) return 'status-error';
        if (s.includes('exec')) return 'status-running';
        if (s.includes('pend')) return 'status-pending';
        return 'status-unknown';
    };

    const showError = (message) => {
        errorDisplay.textContent = `Error: ${message}`;
        errorDisplay.classList.remove('hidden');
    };

    const createJobListWindow = (title, jobList) => {
        // --- Custom Modal Implementation ---

        // 1. Create Modal Structure
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        const content = document.createElement('div');
        content.className = 'modal-content';

        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close-btn';
        closeBtn.innerHTML = '&times;';

        const titleEl = document.createElement('h2');
        titleEl.className = 'modal-title';
        titleEl.textContent = title;

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

        // 2. Assemble Modal
        content.appendChild(closeBtn);
        content.appendChild(titleEl);
        content.appendChild(body);
        overlay.appendChild(content);
        document.body.appendChild(overlay);

        // 3. Show Modal
        // Use requestAnimationFrame to ensure the element is in the DOM before adding the 'visible' class for transitions
        requestAnimationFrame(() => {
            overlay.classList.add('visible');
        });

        // 4. Close Logic
        const closeModal = () => {
            overlay.classList.remove('visible');
            // Remove from DOM after transition
            setTimeout(() => {
                document.body.removeChild(overlay);
            }, 300); // Should match CSS transition time
        };

        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeModal();
            }
        });
    };

    // Add event listeners for widgets
    document.getElementById('widget-running').addEventListener('click', () => {
        createJobListWindow('Running Jobs', apiData.jobs_running);
    });

    document.getElementById('widget-abend').addEventListener('click', () => {
        createJobListWindow('ABEND Jobs', apiData.jobs_abend);
    });

    // Shutdown button logic
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

    // Initial data fetch
    fetchData();
    setInterval(fetchData, 30000);
});
