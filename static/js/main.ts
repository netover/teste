import { Chart, registerables, ChartConfiguration } from 'chart.js';
import Sortable from 'sortablejs';
import { renderSummaryWidget } from './widgets/summaryWidget.ts';
import { renderOQLTableWidget } from './widgets/oqlTableWidget.ts';
import { renderOQLChartWidget } from './widgets/oqlChartWidget.ts';
import { createJobDetailWindow } from './ui_helpers.ts';
import { RealtimeMonitoring } from './realtime-monitoring.ts';
import { JobStream } from './models.ts';
import '../css/style.css';

// Initialize Chart.js
Chart.register(...registerables);

// --- Type Definitions ---
interface WidgetConfig {
    id: string;
    type: 'summary_count' | 'oql_table' | 'oql_chart' | 'error';
    [key: string]: any; // Allow other properties
}

interface ApiData {
    job_streams?: JobStream[];
    workstations?: any[];
    [key: string]: any;
}

interface ChartManager {
    charts: Map<string, Chart>;
    createChart(widgetId: string, config: ChartConfiguration): void;
    destroyChart(widgetId: string): void;
    destroyAllCharts(): void;
}

/**
 * Main JavaScript file for the HWA Dashboard.
 * This file acts as an orchestrator, handling data fetching, state management,
 * and delegating UI rendering to specialized widget modules.
 */
document.addEventListener('DOMContentLoaded', async () => {
    // --- DOM Element References ---
    const widgetsContainer = document.getElementById('summary-widgets') as HTMLElement;
    const jobStreamsGrid = document.getElementById('job-streams-grid') as HTMLElement;
    const workstationsGrid = document.getElementById('workstations-grid') as HTMLElement;
    const loadingIndicator = document.getElementById('loading-indicator') as HTMLElement;
    const errorDisplay = document.getElementById('error-display') as HTMLElement;

    // --- Global State ---
    let apiData: ApiData = {};
    let dashboardLayout: WidgetConfig[] = [];
    let sortedLayout: WidgetConfig[] = [];

    // --- Chart Manager ---
    const chartManager: ChartManager = {
        charts: new Map<string, Chart>(),
        createChart(widgetId: string, config: ChartConfiguration) {
            this.destroyChart(widgetId);
            const canvas = document.querySelector<HTMLCanvasElement>(`#${widgetId} canvas`);
            if (canvas) {
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    this.charts.set(widgetId, new Chart(ctx, config));
                }
            }
        },
        destroyChart(widgetId: string) {
            if (this.charts.has(widgetId)) {
                this.charts.get(widgetId)?.destroy();
                this.charts.delete(widgetId);
            }
        },
        destroyAllCharts() {
            for (const widgetId of this.charts.keys()) {
                this.destroyChart(widgetId);
            }
        }
    };

    const sortLayout = (): void => {
        const savedOrderJSON = localStorage.getItem('dashboardWidgetOrder');
        const savedOrder = savedOrderJSON ? JSON.parse(savedOrderJSON) : null;
        const layoutMap = new Map(dashboardLayout.map(item => [item.id, item]));
        sortedLayout = (savedOrder && savedOrder.length === dashboardLayout.length)
            ? savedOrder.map((id: string) => layoutMap.get(id)).filter(Boolean) as WidgetConfig[]
            : [...dashboardLayout];
    };

    const renderWidgets = (): void => {
        if (!widgetsContainer) return;
        chartManager.destroyAllCharts();
        widgetsContainer.innerHTML = '';

        sortedLayout.forEach(widgetConfig => {
            let widgetEl: HTMLElement | undefined;
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

    const initDragAndDrop = (): void => {
        if (!widgetsContainer) return;
        new Sortable(widgetsContainer, {
            animation: 150,
            ghostClass: 'widget-ghost',
            onEnd: () => {
                const newOrder = [...widgetsContainer.children].map(widget => widget.id);
                localStorage.setItem('dashboardWidgetOrder', JSON.stringify(newOrder));
            }
        });
    };

    const fetchDashboardData = async (): Promise<boolean> => {
        if (jobStreamsGrid && !jobStreamsGrid.hasChildNodes()) loadingIndicator.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        try {
            const response = await fetch('/api/dashboard_data');
            const data: ApiData = await response.json();
            loadingIndicator.classList.add('hidden');
            if ((data as any).error) throw new Error((data as any).error);

            const hasChanged = JSON.stringify(apiData) !== JSON.stringify(data);
            apiData = data;

            if (hasChanged) {
                renderWidgets();
                renderJobStreams(data.job_streams || []);
                renderWorkstations(data.workstations || []);
            }
            return hasChanged;
        } catch (error) {
            loadingIndicator.classList.add('hidden');
            showError((error as Error).message);
            return false;
        }
    };

    const renderJobStreams = (jobStreams: JobStream[]): void => {
        if (!jobStreamsGrid) return;
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
            card.addEventListener('click', () => createJobDetailWindow(js));
            jobStreamsGrid.appendChild(card);
        });
    };

    const renderWorkstations = (workstations: any[]): void => {
        if (!workstationsGrid) return;
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

    const getStatusClass = (status: string): string => {
        if (!status) return 'status-unknown';
        const s = status.toLowerCase();
        if (s.includes('succ') || s.includes('link')) return 'status-success';
        if (s.includes('error') || s.includes('abend')) return 'status-error';
        if (s.includes('exec')) return 'status-running';
        if (s.includes('pend')) return 'status-pending';
        return 'status-unknown';
    };

    const showError = (message: string): void => {
        errorDisplay.innerHTML = message ? `<i class="fas fa-exclamation-triangle"></i> ${message}` : '';
        errorDisplay.classList.toggle('hidden', !message);
    };

    const setupShutdown = (): void => {
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
        minInterval: 15000, maxInterval: 180000, currentInterval: 30000, timerId: null as number | null,
        start() { this.stop(); const loop = async () => { const hasChanges = await fetchDashboardData(); this.adapt(hasChanges); this.timerId = window.setTimeout(loop, this.currentInterval); }; loop(); },
        stop() { if (this.timerId) { clearTimeout(this.timerId); this.timerId = null; console.log("Adaptive poller stopped."); } },
        adapt(hasChanges: boolean) { this.currentInterval = hasChanges ? this.minInterval : Math.min(this.currentInterval * 1.2, this.maxInterval); }
    };

    const handleJobAction = async (e: Event): Promise<void> => {
        const { planId, jobId, action, closeModal } = (e as CustomEvent).detail;
        showError('');
        try {
            const response = await fetch(`/api/plan/${planId}/job/${jobId}/action/${action}`, {
                method: 'PUT',
                headers: { 'X-API-Key': 'your_api_key_here_if_needed' }
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || `Failed to send ${action} command.`);
            alert(result.message || `Successfully sent ${action} command.`);
            if (closeModal) closeModal();
            fetchDashboardData();
        } catch (error) {
            console.error(`${action} action failed:`, error);
            showError(`Error performing ${action} action: ${(error as Error).message}`);
        }
    };

    const fetchLayout = async (): Promise<WidgetConfig[]> => {
        try {
            const response = await fetch('/api/dashboard_layout');
            if (!response.ok) throw new Error('Could not load layout.');
            return await response.json();
        } catch (error) {
            showError((error as Error).message);
            return [{ type: 'error', id: 'layout-error', message: (error as Error).message }];
        }
    };

    // --- Application Initialization ---
    dashboardLayout = await fetchLayout();
    sortLayout();
    renderWidgets();
    initDragAndDrop();
    adaptivePoller.start();
    setupShutdown();

    // --- WebSocket Initialization ---
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/monitoring`;
    const realtimeMonitoring = new RealtimeMonitoring(wsUrl);
    realtimeMonitoring.connect();

    document.addEventListener('websocket:connected', () => adaptivePoller.stop());
    document.addEventListener('job-action', handleJobAction);
});
