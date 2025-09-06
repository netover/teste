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

    const chartManager = {
        charts: new Map(),
        createChart(widgetId, config) {
            this.destroyChart(widgetId); // Ensure no old chart lingers
            const canvas = document.querySelector(`#${widgetId} canvas`);
            if (canvas) {
                const ctx = canvas.getContext('2d');
                const newChart = new Chart(ctx, config);
                this.charts.set(widgetId, newChart);
            }
        },
        destroyChart(widgetId) {
            if (this.charts.has(widgetId)) {
                this.charts.get(widgetId).destroy();
                this.charts.delete(widgetId);
                console.log(`Chart ${widgetId} destroyed.`);
            }
        },
        destroyAllCharts() {
            for (const widgetId of this.charts.keys()) {
                this.destroyChart(widgetId);
            }
        }
    };

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
        chartManager.destroyAllCharts(); // Destroy old charts before re-rendering
        widgetsContainer.innerHTML = '';

        sortedLayout.forEach(widgetConfig => {
            if (widgetConfig.type === 'error') {
                showError(widgetConfig.message);
                return;
            }

            const widgetEl = document.createElement('div');
            widgetEl.id = widgetConfig.id;

            if (widgetConfig.type === 'oql_table') {
                widgetEl.className = 'widget-table'; // A different class for styling
                widgetEl.innerHTML = `
                    <h3 class="widget-title">${widgetConfig.title || 'OQL Table'}</h3>
                    <div class="oql-table-container">
                        <div class="loading-spinner"></div>
                    </div>
                `;
                widgetsContainer.appendChild(widgetEl);
                fetchAndRenderOQLWidget(widgetConfig); // Fetch data for this specific widget
            } else if (widgetConfig.type === 'oql_chart') {
                widgetEl.className = 'widget-chart';
                widgetEl.innerHTML = `
                    <h3 class="widget-title">${widgetConfig.title || 'OQL Chart'}</h3>
                    <div class="oql-chart-container">
                        <canvas></canvas>
                    </div>
                `;
                widgetsContainer.appendChild(widgetEl);
                fetchAndRenderOQLChart(widgetConfig);
            } else { // Default to summary_count
                widgetEl.className = `widget ${widgetConfig.color_class || ''}`;
                widgetEl.innerHTML = `
                    <i class="widget-icon ${widgetConfig.icon || 'fas fa-question-circle'}"></i>
                    <span class="widget-value">--</span>
                    <span class="widget-label">${widgetConfig.label}</span>
                `;

                if (widgetConfig.modal_data_key && widgetConfig.modal_title) {
                    widgetEl.addEventListener('click', () => {
                        const itemList = apiData[widgetConfig.modal_data_key] || [];
                        const renderFunc = itemRenderers[widgetConfig.modal_item_renderer];
                        if (typeof renderFunc === 'function') {
                            createListWindow(widgetConfig.modal_title, itemList, renderFunc);
                        }
                    });
                }
                widgetsContainer.appendChild(widgetEl);
            }
        });
    };

    const fetchAndRenderOQLWidget = async (widgetConfig) => {
        const container = document.querySelector(`#${widgetConfig.id} .oql-table-container`);
        if (!container) return;

        try {
            const source = widgetConfig.oql_source || 'plan';
            const query = encodeURIComponent(widgetConfig.oql_query);
            const response = await fetch(`/api/oql?q=${query}&source=${source}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch OQL data.');
            }
            renderOQLTable(container, data);
        } catch (error) {
            container.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
        }
    };

    const renderOQLTable = (container, data) => {
        if (!Array.isArray(data) || data.length === 0) {
            container.innerHTML = '<p>No results found for this query.</p>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'oql-result-table';

        // Create table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        const headers = Object.keys(data[0]);
        headers.forEach(key => {
            const th = document.createElement('th');
            th.textContent = key;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Create table body
        const tbody = document.createElement('tbody');
        data.forEach(rowData => {
            const row = document.createElement('tr');
            headers.forEach(header => {
                const td = document.createElement('td');
                let value = rowData[header];
                if (typeof value === 'object' && value !== null) {
                    value = JSON.stringify(value, null, 2); // Pretty print nested objects
                    td.innerHTML = `<pre><code>${value}</code></pre>`;
                } else {
                    td.textContent = value;
                }
                row.appendChild(td);
            });
            tbody.appendChild(row);
        });
        table.appendChild(tbody);

        container.innerHTML = ''; // Clear loading spinner
        container.appendChild(table);
    };

    const fetchAndRenderOQLChart = async (widgetConfig) => {
        const container = document.querySelector(`#${widgetConfig.id} .oql-chart-container`);
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner"></div>';

        try {
            const source = widgetConfig.oql_source || 'plan';
            const query = encodeURIComponent(widgetConfig.oql_query);
            const response = await fetch(`/api/oql?q=${query}&source=${source}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to fetch OQL data.');
            }
            renderOQLChart(container, data, widgetConfig);
        } catch (error) {
            container.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
        }
    };

    const renderOQLChart = (container, data, config) => {
        if (!Array.isArray(data) || data.length === 0) {
            container.innerHTML = '<p>No data for this chart.</p>';
            return;
        }

        const { chart_type, label_column, data_column } = config;
        if (!label_column || !data_column) {
            container.innerHTML = '<p class="error-message">Error: Label and Data columns must be configured for this chart.</p>';
            return;
        }

        const labels = data.map(item => item[label_column]);
        const values = data.map(item => item[data_column]);

        container.innerHTML = ''; // Clear spinner
        const chartConfig = {
            type: chart_type || 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: config.title || 'OQL Chart',
                    data: values,
                    backgroundColor: [ // Add some default colors
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(54, 162, 235, 0.5)',
                        'rgba(255, 206, 86, 0.5)',
                        'rgba(75, 192, 192, 0.5)',
                        'rgba(153, 102, 255, 0.5)',
                        'rgba(255, 159, 64, 0.5)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: chart_type === 'pie' || chart_type === 'doughnut', // Only show legend for pie/doughnut
                    }
                }
            }
        };

        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        chartManager.createChart(config.id, chartConfig);
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
            return renderData(data); // Return the boolean from renderData
        } catch (error) {
            loadingIndicator.classList.add('hidden');
            showError(error.message);
            return false; // Assume no changes on error
        }
    };

    /**
     * Populates the UI with data from the API.
     * @returns {boolean} - True if the data has changed, false otherwise.
     */
    const renderData = (data) => {
        const hasChanged = JSON.stringify(apiData) !== JSON.stringify(data);
        apiData = data;

        if (!hasChanged) {
            console.log("No data changes detected.");
            return false;
        }

        console.log("Data has changed, re-rendering UI components.");

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

    const createListWindow = (title, itemList, renderItem) => {
        let listHtml = '<ul>';
        if (itemList && itemList.length > 0) {
            itemList.forEach(item => { listHtml += renderItem(item); });
        } else {
            listHtml += `<li>No items to display in this category.</li>`;
        }
        listHtml += '</ul>';

        // Use the generic modal creator from ui_helpers.js
        createModal(title, listHtml);
    };

    const createJobDetailWindow = (jobStream) => {
        const { jobStreamName, workstationName, status, startTime, id: jobId } = jobStream;
        const planId = 'current';

        const bodyHTML = `
            <p><strong>Name:</strong> ${jobStreamName}</p>
            <p><strong>Workstation:</strong> ${workstationName}</p>
            <p><strong>Status:</strong> <span class="status ${getStatusClass(status)}">${status}</span></p>
            <p><strong>Start Time:</strong> ${startTime ? new Date(startTime).toLocaleString() : 'N/A'}</p>
            <p><strong>Job ID:</strong> ${jobId}</p>
            <p><strong>Plan ID:</strong> ${planId}</p>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-action="rerun">Rerun</button>
                <button class="btn btn-warning" data-action="hold">Hold</button>
                <button class="btn btn-info" data-action="release">Release</button>
                <button class="btn btn-danger" data-action="cancel">Cancel</button>
            </div>
        `;

        createModal(`Job Details: ${jobStreamName}`, bodyHTML, (modal, closeModal) => {
            modal.querySelectorAll('.modal-footer button').forEach(btn => {
                btn.addEventListener('click', () => {
                    const action = btn.dataset.action;
                    if (confirm(`Are you sure you want to ${action} job "${jobStreamName}"?`)) {
                        performJobAction(planId, jobId, action, closeModal);
                    }
                });
            });
        });
    };

    const performJobAction = async (planId, jobId, action, callbackOnSuccess) => {
        showError(''); // Clear previous errors
        try {
            const response = await fetch(`/api/plan/${planId}/job/${jobId}/action/${action}`, {
                method: 'PUT',
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || `Failed to send ${action} command.`);
            }
            alert(result.message || `Successfully sent ${action} command.`);
            if (callbackOnSuccess) callbackOnSuccess();
            fetchData(); // Refresh data to reflect the change
        } catch (error) {
            console.error(`${action} action failed:`, error);
            showError(`Error performing ${action} action: ${error.message}`);
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

    const adaptivePoller = {
        minInterval: 15000, // 15 seconds
        maxInterval: 180000, // 3 minutes
        currentInterval: 30000, // Start at 30 seconds
        timerId: null,

        start() {
            this.stop(); // Ensure no multiple timers running
            const loop = async () => {
                const hasChanges = await fetchData();
                this.adapt(hasChanges);
                this.timerId = setTimeout(loop, this.currentInterval);
            };
            loop(); // Start the first iteration immediately
        },

        stop() {
            if (this.timerId) {
                clearTimeout(this.timerId);
                this.timerId = null;
            }
        },

        adapt(hasChanges) {
            if (hasChanges) {
                // If there were changes, poll more frequently
                this.currentInterval = this.minInterval;
            } else {
                // If no changes, gradually slow down polling
                this.currentInterval = Math.min(this.currentInterval * 1.2, this.maxInterval);
            }
            console.log(`Polling interval adapted to ${this.currentInterval / 1000}s`);
        }
    };

    // --- Application Initialization ---
    sortLayout();           // 1. Determine the correct widget order.
    renderWidgets();        // 2. Build the widget UI.
    initDragAndDrop();      // 3. Make the widgets draggable.
    adaptivePoller.start(); // 4. Start the adaptive polling.
    setupShutdown();        // Set up the shutdown button.
});
