/**
 * Main JavaScript file for the HWA Dashboard.
 * Handles API data fetching, UI rendering, and all interactivity
 * for the main dashboard page, including dynamic, draggable widgets.
 */
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const widgetsContainer = document.getElementById('summary-widgets');
    const jobStreamsGrid = document.getElementById('job-streams-grid');
    const workstationsGrid = document.getElementById('workstations-grid');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');

    // --- Global State ---
    // `dashboardLayout` is injected from the backend via a script tag in index.html
    let apiData = {}; // Caches the latest data from the backend.
    let sortedLayout = []; // Will hold the layout sorted by user preference.

    // --- Render Functions for Modal Lists ---
    const itemRenderers = {
        renderJobItem: job => `<li><strong>${job.jobStreamName || 'N/A'}</strong> on ${job.workstationName || 'N/A'} (${job.status})</li>`,
        renderWorkstationItem: ws => `<li><strong>${ws.name}</strong> (${ws.type}) - Status: <span class="status ${getStatusClass(ws.status)}">${ws.status}</span></li>`
    };

    /**
     * Sorts the layout configuration based on a saved order in localStorage.
     * If no order is saved, it uses the default order from the JSON file.
     */
    const sortLayout = () => {
        const savedOrder = JSON.parse(localStorage.getItem('dashboardWidgetOrder'));
        const layoutMap = new Map(dashboardLayout.map(item => [item.id, item]));

        if (savedOrder && savedOrder.length === dashboardLayout.length) {
            // Use saved order, filtering out any IDs that no longer exist in the config
            sortedLayout = savedOrder
                .map(id => layoutMap.get(id))
                .filter(Boolean); // Filter out undefined in case config changed
        } else {
            // Use default order
            sortedLayout = [...dashboardLayout];
        }
    };

    /**
     * Renders the entire widget section based on the sorted layout.
     */
    const renderWidgets = () => {
        if (!widgetsContainer) return;
        widgetsContainer.innerHTML = '';

        sortedLayout.forEach(widgetConfig => {
            if (widgetConfig.type === 'error') {
                showError(widgetConfig.message);
                return;
            }
            const widgetEl = document.createElement('div');
            widgetEl.className = `widget ${widgetConfig.color_class || ''}`;
            widgetEl.id = widgetConfig.id;

            widgetEl.innerHTML = `
                <i class="widget-icon ${widgetConfig.icon || 'fas fa-question-circle'}"></i>
                <span class="widget-value">--</span>
                <span class="widget-label">${widgetConfig.label}</span>
            `;

            if (widgetConfig.modal_data_key && widgetConfig.modal_title) {
                widgetEl.addEventListener('click', (e) => {
                    const itemList = apiData[widgetConfig.modal_data_key] || [];
                    const renderFunc = itemRenderers[widgetConfig.modal_item_renderer];
                    if (typeof renderFunc === 'function') {
                        createListWindow(widgetConfig.modal_title, itemList, e.currentTarget, renderFunc);
                    }
                });
            }
            widgetsContainer.appendChild(widgetEl);
        });
    };

    /**
     * Initializes SortableJS to make widgets draggable and saves the new order.
     */
    const initDragAndDrop = () => {
        if (!widgetsContainer || typeof Sortable === 'undefined') return;

        new Sortable(widgetsContainer, {
            animation: 150,
            ghostClass: 'widget-ghost',
            onEnd: () => {
                const newOrder = [...widgetsContainer.children].map(widget => widget.id);
                localStorage.setItem('dashboardWidgetOrder', JSON.stringify(newOrder));
            }
        });
    };

    /**
     * Fetches the latest dashboard data from the backend API.
     */
    const fetchData = async () => {
        if (!jobStreamsGrid.hasChildNodes()) loadingIndicator.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        try {
            const response = await fetch('/api/dashboard_data');
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
     * Populates the UI with data from the API.
     */
    const renderData = (data) => {
        apiData = data;

        sortedLayout.forEach(widgetConfig => {
            if (widgetConfig.api_metric) {
                const widgetValueEl = document.querySelector(`#${widgetConfig.id} .widget-value`);
                if (widgetValueEl) {
                    widgetValueEl.textContent = data[widgetConfig.api_metric] ?? 0;
                }
            }
        });

        renderJobStreams(data.job_streams || []);
        renderWorkstations(data.workstations || []);
    };

    const renderJobStreams = (jobStreams) => {
        console.log('Rendering job streams:', jobStreams);
        jobStreamsGrid.innerHTML = '';
        if (jobStreams.length === 0) { jobStreamsGrid.innerHTML = '<p>No job streams found.</p>'; return; }
        jobStreams.forEach(js => {
            // Each job stream card now gets a click listener to open a detail view
            const card = document.createElement('div');
            card.className = 'job-stream-card';
            card.dataset.jobId = js.id; // Store job ID for actions
            card.dataset.planId = 'current'; // Assuming 'current' plan for now

            const statusClass = getStatusClass(js.status);
            card.innerHTML = `
                <h3>${js.jobStreamName || 'N/A'}</h3>
                <p><strong>Workstation:</strong> ${js.workstationName || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status ${statusClass}">${js.status || 'N/A'}</span></p>
                <p><strong>Start Time:</strong> ${js.startTime ? new Date(js.startTime).toLocaleString() : 'N/A'}</p>
            `;
            card.addEventListener('click', () => createJobDetailWindow(js));
            jobStreamsGrid.appendChild(card);
        });
    };

    const renderWorkstations = (workstations) => {
        workstationsGrid.innerHTML = '';
        if (workstations.length === 0) { workstationsGrid.innerHTML = '<p>No workstations found.</p>'; return; }
        workstations.forEach(ws => {
            const card = document.createElement('div');
            card.className = 'workstation-card';
            const statusClass = getStatusClass(ws.status);
            card.innerHTML = `<h3>${ws.name || 'N/A'}</h3><p><strong>Type:</strong> ${ws.type || 'N/A'}</p><p><strong>Status:</strong> <span class="status ${statusClass}">${ws.status || 'N/A'}</span></p>`;
            workstationsGrid.appendChild(card);
        });
    };

    const getStatusClass = (status) => {
        if (!status) return 'status-unknown';
        const s = status.toLowerCase();
        if (s.includes('succ') || s.includes('link')) return 'status-success';
        if (s.includes('error') || s.includes('abend')) return 'status-error';
        if (s.includes('exec')) return 'status-running';
        if (s.includes('pend')) return 'status-pending';
        return 'status-unknown';
    };

    const showError = (message) => {
        errorDisplay.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        errorDisplay.classList.remove('hidden');
    };

    const createListWindow = (title, itemList, originElement, renderItem) => {
        // This function remains the same as before.
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
        if (itemList && itemList.length > 0) {
            itemList.forEach(item => { listHtml += renderItem(item); });
        } else {
            listHtml += `<li>No items to display in this category.</li>`;
        }
        listHtml += '</ul>';
        body.innerHTML = listHtml;
        content.append(closeBtn, titleEl, body);
        overlay.appendChild(content);
        document.body.appendChild(overlay);

        const originRect = originElement.getBoundingClientRect();
        content.style.left = `${originRect.left + (originRect.width / 2)}px`;
        content.style.top = `${originRect.top + (originRect.height / 2)}px`;
        content.style.transform = 'scale(0)';
        content.style.opacity = '0';

        requestAnimationFrame(() => {
            overlay.classList.add('visible');
            content.classList.add('animated-open');
        });

        const closeModal = () => {
            content.classList.remove('animated-open');
            setTimeout(() => { if (document.body.contains(overlay)) document.body.removeChild(overlay); }, 300);
        };
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });

        let isDragging = false, offset = { x: 0, y: 0 };
        titleEl.style.cursor = 'grab';
        titleEl.addEventListener('mousedown', e => {
            isDragging = true;
            offset = { x: e.clientX - content.offsetLeft, y: e.clientY - content.offsetTop };
            titleEl.style.cursor = 'grabbing';
        });
        const onMouseMove = e => {
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

        closeBtn.addEventListener('click', () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        }, { once: true });
    };

    const createJobDetailWindow = (jobStream) => {
        const { jobStreamName, workstationName, status, startTime, id: jobId } = jobStream;
        const planId = 'current'; // Hardcoded for now

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        const content = document.createElement('div');
        content.className = 'modal-content';

        content.innerHTML = `
            <button class="modal-close-btn">&times;</button>
            <h2 class="modal-title">Job Stream Details</h2>
            <div class="modal-body">
                <p><strong>Name:</strong> ${jobStreamName}</p>
                <p><strong>Workstation:</strong> ${workstationName}</p>
                <p><strong>Status:</strong> <span class="status ${getStatusClass(status)}">${status}</span></p>
                <p><strong>Start Time:</strong> ${startTime ? new Date(startTime).toLocaleString() : 'N/A'}</p>
                <p><strong>Job ID:</strong> ${jobId}</p>
                <p><strong>Plan ID:</strong> ${planId}</p>
            </div>
            <div class="modal-footer">
                <button id="cancel-job-btn" class="btn-danger">Cancel Job</button>
            </div>
        `;

        document.body.appendChild(overlay);
        overlay.appendChild(content);

        // Animation and closing logic
        requestAnimationFrame(() => {
            overlay.classList.add('visible');
            content.classList.add('animated-open');
        });

        const closeModal = () => {
            content.classList.remove('animated-open');
            setTimeout(() => { if (document.body.contains(overlay)) document.body.removeChild(overlay); }, 300);
        };

        content.querySelector('.modal-close-btn').addEventListener('click', closeModal);
        overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });

        // Action button logic
        content.querySelector('#cancel-job-btn').addEventListener('click', () => {
            if (confirm(`Are you sure you want to cancel job "${jobStreamName}"?`)) {
                cancelJob(planId, jobId, closeModal);
            }
        });
    };

    const cancelJob = async (planId, jobId, callbackOnSuccess) => {
        showError(''); // Clear previous errors
        try {
            const response = await fetch(`/api/plan/${planId}/job/${jobId}/action/cancel`, {
                method: 'PUT',
            });
            const result = await response.json();
            if (!response.ok || result.error) {
                throw new Error(result.error || `Failed to send cancel command. Status: ${response.status}`);
            }
            alert(result.message || 'Successfully sent cancel command.');
            if (callbackOnSuccess) callbackOnSuccess();
            fetchData(); // Refresh data to reflect the change
        } catch (error) {
            console.error('Cancellation failed:', error);
            showError(`Error cancelling job: ${error.message}`);
        }
    };

    const setupShutdown = () => {
        const shutdownBtn = document.getElementById('shutdown-btn');
        if (shutdownBtn) {
            shutdownBtn.addEventListener('click', async () => {
                if (confirm('Are you sure you want to shut down the application?')) {
                    try { await fetch('/shutdown', { method: 'POST' }); }
                    finally { document.body.innerHTML = '<header><h1>Application Shut Down</h1></header><main><p>You can now close this browser tab.</p></main>'; }
                }
            });
        }
    };

    // Expose fetchData to the window for testing purposes
    window.fetchData = fetchData;

    // --- Application Initialization ---
    sortLayout();           // 1. Determine the correct widget order.
    renderWidgets();        // 2. Build the widget UI.
    initDragAndDrop();      // 3. Make the widgets draggable.
    fetchData();            // 4. Fetch data to populate the UI.
    setInterval(fetchData, 30000); // Refresh data periodically.
    setupShutdown();        // Set up the shutdown button.
});
