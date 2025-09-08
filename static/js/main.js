import { renderSummaryWidget, updateSummaryWidget } from './widgets/summaryWidget.js';
import { renderOQLTableWidget } from './widgets/oqlTableWidget.js';
import { renderOQLChartWidget } from './widgets/oqlChartWidget.js';
import { createJobDetailWindow } from './ui_helpers.js';

/**
 * Main JavaScript file for the HWA Dashboard.
 * This file acts as an orchestrator, handling data fetching, state management,
 * and delegating UI rendering to specialized widget modules.
 */
document.addEventListener('DOMContentLoaded', () => {
    // DOM Element References
    const widgetsContainer = document.getElementById('summary-widgets');
    const jobStreamsGrid = document.getElementById('job-streams-grid');
    const workstationsGrid = document.getElementById('workstations-grid');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');

    // Global State
    let apiData = {};
    let sortedLayout = [];

    // Chart Manager
    const chartManager = {
        charts: new Map(),
        createChart(widgetId, config) {
            this.destroyChart(widgetId);
            const canvas = document.querySelector(`#${widgetId} canvas`);
            if (canvas) {
                const ctx = canvas.getContext('2d');
                this.charts.set(widgetId, new Chart(ctx, config));
            }
        },
        destroyChart(widgetId) {
            if (this.charts.has(widgetId)) {
                this.charts.get(widgetId).destroy();
                this.charts.delete(widgetId);
            }
        },
        destroyAllCharts() {
            for (const widgetId of this.charts.keys()) {
                this.destroyChart(widgetId);
            }
        }
    };

    const sortLayout = () => {
        const savedOrder = JSON.parse(localStorage.getItem('dashboardWidgetOrder'));
        const layoutMap = new Map(dashboardLayout.map(item => [item.id, item]));
        sortedLayout = (savedOrder && savedOrder.length === dashboardLayout.length)
            ? savedOrder.map(id => layoutMap.get(id)).filter(Boolean)
            : [...dashboardLayout];
    };

    const renderWidgets = () => {
        if (!widgetsContainer) return;
        chartManager.destroyAllCharts();
        widgetsContainer.innerHTML = '';

        sortedLayout.forEach(widgetConfig => {
            let widgetEl;
            switch (widgetConfig.type) {
                case 'oql_table':
                    widgetEl = renderOQLTableWidget(widgetConfig);
                    break;
                case 'oql_chart':
                    widgetEl = renderOQLChartWidget(widgetConfig, chartManager);
                    break;
                case 'summary_count':
                    widgetEl = renderSummaryWidget(widgetConfig, apiData);
                    break;
                case 'error':
                    showError(widgetConfig.message);
                    return;
                default:
                    console.warn(`Unknown widget type: ${widgetConfig.type}`);
                    return;
            }
            if (widgetEl) {
                widgetsContainer.appendChild(widgetEl);
            }
        });
    };

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

    const fetchData = async () => {
        if (!jobStreamsGrid.hasChildNodes()) loadingIndicator.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        try {
            const response = await fetch('/api/dashboard_data');
            const data = await response.json();
            loadingIndicator.classList.add('hidden');
            if (data.error) throw new Error(data.error);

            const hasChanged = JSON.stringify(apiData) !== JSON.stringify(data);
            apiData = data;

            if (hasChanged) {
                // The most robust way to update is to simply re-render everything.
                renderWidgets();
                renderJobStreams(data.job_streams || []);
                renderWorkstations(data.workstations || []);
            }
            return hasChanged;
        } catch (error) {
            loadingIndicator.classList.add('hidden');
            showError(error.message);
            return false;
        }
    };

    const renderJobStreams = (jobStreams) => {
        jobStreamsGrid.innerHTML = '';
        if (jobStreams.length === 0) {
            jobStreamsGrid.innerHTML = '<p>No job streams found.</p>';
            return;
        }
        jobStreams.forEach(js => {
            const card = document.createElement('div');
            card.className = 'job-stream-card';
            card.dataset.jobId = js.id;
            card.dataset.jobName = js.jobStreamName;
            card.dataset.planId = 'current';

            const statusClass = getStatusClass(js.status);
            card.innerHTML = `
                <h3>${js.jobStreamName || 'N/A'}</h3>
                <p><strong>Workstation:</strong> ${js.workstationName || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status-badge ${statusClass}">${js.status || 'N/A'}</span></p>
                <p><strong>Start Time:</strong> ${js.startTime ? new Date(js.startTime).toLocaleString() : 'N/A'}</p>
            `;
            card.addEventListener('click', () => createJobDetailWindow(js, showError, fetchData));
            jobStreamsGrid.appendChild(card);
        });
    };

    const renderWorkstations = (workstations) => {
        workstationsGrid.innerHTML = '';
        if (workstations.length === 0) {
            workstationsGrid.innerHTML = '<p>No workstations found.</p>';
            return;
        }
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
        errorDisplay.innerHTML = message ? `<i class="fas fa-exclamation-triangle"></i> ${message}` : '';
        errorDisplay.classList.toggle('hidden', !message);
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

    const adaptivePoller = {
        minInterval: 15000, maxInterval: 180000, currentInterval: 30000, timerId: null,
        start() {
            this.stop();
            const loop = async () => {
                const hasChanges = await fetchData();
                this.adapt(hasChanges);
                this.timerId = setTimeout(loop, this.currentInterval);
            };
            loop();
        },
        stop() {
            if (this.timerId) {
                clearTimeout(this.timerId);
                this.timerId = null;
                console.log("Adaptive poller stopped.");
            }
        },
        adapt(hasChanges) {
            this.currentInterval = hasChanges ? this.minInterval : Math.min(this.currentInterval * 1.2, this.maxInterval);
        }
    };

    // --- Application Initialization ---
    sortLayout();
    renderWidgets();
    initDragAndDrop();
    adaptivePoller.start();
    setupShutdown();

    document.addEventListener('websocket:connected', () => {
        adaptivePoller.stop();
    });
});
