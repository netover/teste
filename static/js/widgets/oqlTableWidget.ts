interface OQLWidgetConfig {
    id: string;
    title?: string;
    oql_source?: 'plan' | 'model';
    oql_query: string;
}

type OQLData = Record<string, any>[];

function renderOQLTable(container: HTMLElement, data: OQLData): void {
    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p>No results found for this query.</p>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'oql-result-table';

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

    const tbody = document.createElement('tbody');
    data.forEach(rowData => {
        const row = document.createElement('tr');
        headers.forEach(header => {
            const td = document.createElement('td');
            let value = rowData[header];
            if (typeof value === 'object' && value !== null) {
                value = JSON.stringify(value, null, 2);
                td.innerHTML = `<pre><code>${value}</code></pre>`;
            } else {
                td.textContent = String(value);
            }
            row.appendChild(td);
        });
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(table);
}

async function fetchAndRender(container: HTMLElement, widgetConfig: OQLWidgetConfig): Promise<void> {
    if (!container) return;

    try {
        const source = widgetConfig.oql_source || 'plan';
        const query = encodeURIComponent(widgetConfig.oql_query);
        const response = await fetch(`/api/oql?q=${query}&source=${source}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to fetch OQL data.');
        }
        renderOQLTable(container, data);
    } catch (error) {
        container.innerHTML = `<p class="error-message">Error: ${(error as Error).message}</p>`;
    }
}

export function renderOQLTableWidget(widgetConfig: OQLWidgetConfig): HTMLElement {
    const widgetEl = document.createElement('div');
    widgetEl.id = widgetConfig.id;
    widgetEl.className = 'widget-table';

    const tableContainer = document.createElement('div');
    tableContainer.className = 'oql-table-container';
    tableContainer.innerHTML = '<div class="loading-spinner"></div>';

    widgetEl.innerHTML = `<h3 class="widget-title">${widgetConfig.title || 'OQL Table'}</h3>`;
    widgetEl.appendChild(tableContainer);

    fetchAndRender(tableContainer, widgetConfig);

    return widgetEl;
}
