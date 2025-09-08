import { createListWindow } from '../ui_helpers.ts';
import { JobStream } from '../models'; // Assuming a models.ts file for shared interfaces

// Define interfaces for the data structures
interface WidgetConfig {
    id: string;
    color_class?: string;
    api_metric: string;
    icon?: string;
    label: string;
    modal_data_key?: string;
    modal_title?: string;
    modal_item_renderer?: keyof typeof itemRenderers;
}

interface ApiData {
    [key: string]: any; // Allow any string keys for now
}

const itemRenderers = {
    renderJobItem: (job: JobStream) => `<li><strong>${job.jobStreamName || 'N/A'}</strong> on ${job.workstationName || 'N/A'} (${job.status})</li>`,
    renderWorkstationItem: (ws: any) => `<li><strong>${ws.name}</strong> (${ws.type}) - Status: <span class="status">${ws.status}</span></li>`
};

export function renderSummaryWidget(widgetConfig: WidgetConfig, apiData: ApiData): HTMLElement {
    const widgetEl = document.createElement('div');
    widgetEl.id = widgetConfig.id;
    widgetEl.className = `widget ${widgetConfig.color_class || ''}`;

    const value = apiData[widgetConfig.api_metric] ?? '--';

    widgetEl.innerHTML = `
        <i class="widget-icon ${widgetConfig.icon || 'fas fa-question-circle'}"></i>
        <span class="widget-value">${value}</span>
        <span class="widget-label">${widgetConfig.label}</span>
    `;

    if (widgetConfig.modal_data_key && widgetConfig.modal_title && widgetConfig.modal_item_renderer) {
        widgetEl.addEventListener('click', () => {
            const itemList = apiData[widgetConfig.modal_data_key] || [];
            const renderFunc = itemRenderers[widgetConfig.modal_item_renderer];
            if (typeof renderFunc === 'function') {
                createListWindow(widgetConfig.modal_title, itemList, renderFunc);
            }
        });
    }

    return widgetEl;
}

export function updateSummaryWidget(widgetConfig: WidgetConfig, apiData: ApiData): void {
    const widgetValueEl = document.querySelector<HTMLElement>(`#${widgetConfig.id} .widget-value`);
    if (widgetValueEl) {
        widgetValueEl.textContent = (apiData[widgetConfig.api_metric] ?? 0).toString();
    }
}
