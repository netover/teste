function renderOQLChart(container, data, config, chartManager) {
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
                backgroundColor: [
                    'rgba(255, 99, 132, 0.5)', 'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 206, 86, 0.5)', 'rgba(75, 192, 192, 0.5)',
                    'rgba(153, 102, 255, 0.5)', 'rgba(255, 159, 64, 0.5)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)', 'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: chart_type === 'pie' || chart_type === 'doughnut' }
            }
        }
    };

    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    chartManager.createChart(config.id, chartConfig);
}

async function fetchAndRender(container, widgetConfig, chartManager) {
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
        renderOQLChart(container, data, widgetConfig, chartManager);
    } catch (error) {
        container.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
    }
}

export function renderOQLChartWidget(widgetConfig, chartManager) {
    const widgetEl = document.createElement('div');
    widgetEl.id = widgetConfig.id;
    widgetEl.className = 'widget-chart';

    const chartContainer = document.createElement('div');
    chartContainer.className = 'oql-chart-container';

    widgetEl.innerHTML = `<h3 class="widget-title">${widgetConfig.title || 'OQL Chart'}</h3>`;
    widgetEl.appendChild(chartContainer);

    fetchAndRender(chartContainer, widgetConfig, chartManager);

    return widgetEl;
}
