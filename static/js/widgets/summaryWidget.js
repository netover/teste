import { createListWindow } from '../ui_helpers.js';

const itemRenderers = {
    renderJobItem: job => `<li><strong>${job.jobStreamName || 'N/A'}</strong> on ${job.workstationName || 'N/A'} (${job.status})</li>`,
    renderWorkstationItem: ws => `<li><strong>${ws.name}</strong> (${ws.type}) - Status: <span class="status">${ws.status}</span></li>` // Note: status class might need update
};

export function renderSummaryWidget(widgetConfig, apiData) {
    const widgetEl = document.createElement('div');
    widgetEl.id = widgetConfig.id;
    widgetEl.className = `widget ${widgetConfig.color_class || ''}`;

    const value = apiData[widgetConfig.api_metric] ?? '--';
    console.log(`Rendering summary widget: id=${widgetConfig.id}, value=${value}`);

    widgetEl.innerHTML = `
        <i class="widget-icon ${widgetConfig.icon || 'fas fa-question-circle'}"></i>
        <span class="widget-value">${value}</span>
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

    return widgetEl;
}

export function updateSummaryWidget(widgetConfig, apiData) {
    const widgetValueEl = document.querySelector(`#${widgetConfig.id} .widget-value`);
    if (widgetValueEl) {
        widgetValueEl.textContent = apiData[widgetConfig.api_metric] ?? 0;
    }
}
