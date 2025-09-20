import Sortable from 'sortablejs';
import { createModal } from './ui_helpers.ts';
import '../css/style.css';

// --- Type Definitions ---
interface WidgetConfig {
    id: string;
    type: string;
    [key: string]: any;
}

type WidgetType = 'summary_count' | 'oql_table' | 'oql_chart';

document.addEventListener('DOMContentLoaded', () => {
    const editorContainer = document.getElementById('editor-container') as HTMLElement;
    const messageArea = document.createElement('div');
    messageArea.id = 'message-area';
    messageArea.className = 'hidden';
    let widgetListContainer: HTMLElement;
    let sortableInstance: Sortable;

    let currentLayout: WidgetConfig[] = [];

    const loadLayout = async (): Promise<void> => {
        try {
            const response = await fetch('/api/dashboard_layout');
            if (!response.ok) throw new Error('Could not load layout.');
            currentLayout = await response.json();
            renderWidgetList();
        } catch (error) {
            showMessage(`Error: ${(error as Error).message}`, 'error');
        }
    };

    const renderWidgetList = (): void => {
        widgetListContainer.innerHTML = '';
        if (currentLayout.length === 0) {
            widgetListContainer.innerHTML = '<p>No widgets defined. Add one!</p>';
        }
        currentLayout.forEach((widget) => {
            const widgetEl = createWidgetEditorElement(widget);
            widgetListContainer.appendChild(widgetEl);
        });
        initSortable();
    };

    const createWidgetEditorElement = (widget: WidgetConfig): HTMLElement => {
        const el = document.createElement('div');
        el.className = 'widget-editor-item';
        el.dataset.widgetId = widget.id;
        el.dataset.widgetType = widget.type || 'summary_count';

        let fieldsHTML = '';
        const widgetType = el.dataset.widgetType;

        // Common fields
        fieldsHTML += `
            <div class="form-group">
                <label>Label</label>
                <input type="text" name="label" class="form-control" value="${widget.label || ''}">
            </div>
        `;

        if (widgetType === 'oql_table' || widgetType === 'oql_chart') {
            fieldsHTML += `
                <div class="form-group">
                    <label>OQL Query</label>
                    <textarea name="oql_query" class="form-control">${widget.oql_query || ''}</textarea>
                    <button class="validate-oql-btn btn-secondary">Validate</button>
                    <span class="validate-result"></span>
                </div>
            `;
        }

        if (widgetType === 'summary_count') {
             fieldsHTML += `
                <div class="form-group">
                    <label>API Metric</label>
                    <input type="text" name="api_metric" class="form-control" value="${widget.api_metric || ''}">
                </div>
             `;
        }

        if (widgetType === 'oql_chart') {
            fieldsHTML += `
                <div class="form-group">
                    <label>Chart Type</label>
                    <select name="chart_type" class="form-control">
                        <option value="bar" ${widget.chart_type === 'bar' ? 'selected' : ''}>Bar</option>
                        <option value="pie" ${widget.chart_type === 'pie' ? 'selected' : ''}>Pie</option>
                    </select>
                </div>
            `;
        }


        el.innerHTML = `
            <div class="widget-editor-content">
                <p class="widget-editor-title">Type: ${widgetType}</p>
                ${fieldsHTML}
            </div>
            <div class="widget-editor-controls">
                <button class="remove-widget-btn btn-danger"><i class="fas fa-trash"></i></button>
            </div>
        `;

        el.querySelector<HTMLButtonElement>('.remove-widget-btn')?.addEventListener('click', (e: Event) => {
            e.preventDefault();
            if (confirm('Are you sure you want to remove this widget?')) {
                const widgetIdToRemove = el.dataset.widgetId;
                currentLayout = currentLayout.filter(w => w.id !== widgetIdToRemove);
                el.remove();
            }
        });

        const validateBtn = el.querySelector<HTMLButtonElement>('.validate-oql-btn');
        if (validateBtn) {
            validateBtn.addEventListener('click', (e: Event) => {
                e.preventDefault();
                const textarea = el.querySelector<HTMLTextAreaElement>('textarea[name="oql_query"]');
                const resultSpan = el.querySelector<HTMLSpanElement>('.validate-result');
                if (textarea && resultSpan) {
                    validateOQLQuery(textarea.value, resultSpan);
                }
            });
        }

        return el;
    };

    const validateOQLQuery = async (query: string, resultSpan: HTMLElement): Promise<void> => {
        if (!query) {
            resultSpan.textContent = '✗ Query is empty.';
            resultSpan.className = 'validate-result error';
            return;
        }
        resultSpan.textContent = 'Validating...';
        resultSpan.className = 'validate-result info';

        try {
            const response = await fetch(`/api/oql?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Unknown error');
            }
            resultSpan.textContent = `✓ Query is valid. Found ${data.length} item(s).`;
            resultSpan.className = 'validate-result success';
        } catch (error) {
            resultSpan.textContent = `✗ Invalid query: ${(error as Error).message}`;
            resultSpan.className = 'validate-result error';
        }
    };

    const initSortable = (): void => {
        if (sortableInstance) {
            sortableInstance.destroy();
        }
        sortableInstance = new Sortable(widgetListContainer, {
            animation: 150,
            handle: '.widget-editor-item',
            ghostClass: 'widget-ghost',
            onEnd: () => {
                const newOrder = Array.from(widgetListContainer.children).map(item => (item as HTMLElement).dataset.widgetId);
                currentLayout.sort((a, b) => (newOrder.indexOf(a.id) ?? -1) - (newOrder.indexOf(b.id) ?? -1));
            }
        });
    };

    const showAddWidgetModal = (): void => {
        // Programmatically create the modal content to ensure correctness
        const modalHTML = `
            <div class="form-group">
                <label for="widget-type-select">Widget Type:</label>
                <select id="widget-type-select" class="form-control">
                    <option value="summary_count">Summary Count</option>
                    <option value="oql_table">OQL Table</option>
                    <option value="oql_chart">OQL Chart</option>
                </select>
            </div>
            <div class="form-group">
                <button id="create-widget-btn" class="btn-primary">Create Widget</button>
            </div>
        `;

        const setupCallback = (modalContent: HTMLElement, closeModal: () => void) => {
            const createBtn = modalContent.querySelector<HTMLButtonElement>('#create-widget-btn');
            const typeSelect = modalContent.querySelector<HTMLSelectElement>('#widget-type-select');

            createBtn?.addEventListener('click', () => {
                if (!typeSelect) return;
                const widgetType: WidgetType = typeSelect.value as WidgetType;
                const newWidget: Partial<WidgetConfig> = {
                    id: `widget_${new Date().getTime()}`,
                    type: widgetType,
                    label: "New Widget" // Default label
                };

                // Add more specific defaults based on type if necessary
                if (widgetType === 'summary_count') {
                    newWidget.label = "New Summary";
                    newWidget.api_metric = "total_job_stream_count"; // A sensible default
                } else if (widgetType === 'oql_table') {
                    newWidget.label = "New OQL Table";
                    newWidget.oql_query = "SELECT NAME, STATUS FROM JOB"; // A sensible default
                } else if (widgetType === 'oql_chart') {
                    newWidget.label = "New OQL Chart";
                    newWidget.oql_query = "SELECT STATUS, COUNT(*) FROM JOBSTREAM GROUP BY STATUS"; // A sensible default
                }

                currentLayout.push(newWidget as WidgetConfig);
                renderWidgetList();
                closeModal();
            });
        };
        createModal('Add New Widget', modalHTML, setupCallback);
    };

    const initEditor = (): void => {
        // Clear the container and build the UI programmatically
        editorContainer.innerHTML = '';
        editorContainer.innerHTML = `
            <div class="editor-controls">
                <button id="add-widget-btn" class="btn-primary">Add Widget</button>
                <button id="save-layout-btn" class="btn-success">Save Layout</button>
            </div>
            <div id="widget-list"></div> <!-- This was the missing element -->
        `;
        editorContainer.appendChild(messageArea);

        // Now this will correctly find the element
        widgetListContainer = document.getElementById('widget-list') as HTMLElement;
        if (!widgetListContainer) {
            console.error("Fatal: #widget-list container not found after init.");
            return;
        }

        document.getElementById('add-widget-btn')?.addEventListener('click', showAddWidgetModal);
        document.getElementById('save-layout-btn')?.addEventListener('click', saveLayout);

        loadLayout();
    };

    const saveLayout = async (): Promise<void> => {
        const newLayout: WidgetConfig[] = [];
        const widgetItems = widgetListContainer.querySelectorAll<HTMLElement>('.widget-editor-item');

        widgetItems.forEach(item => {
            const widgetId = item.dataset.widgetId;
            const widgetType = item.dataset.widgetType;

            let widgetData: Partial<WidgetConfig> = { id: widgetId, type: widgetType };

            // Helper to get value from an input
            const getInputValue = (name: string) => (item.querySelector<HTMLInputElement>(`input[name="${name}"]`))?.value || '';
            const getSelectValue = (name: string) => (item.querySelector<HTMLSelectElement>(`select[name="${name}"]`))?.value || '';
            const getTextareaValue = (name: string) => (item.querySelector<HTMLTextAreaElement>(`textarea[name="${name}"]`))?.value || '';

            widgetData.label = getInputValue('label');

            if (widgetType === 'oql_table' || widgetType === 'oql_chart') {
                widgetData.oql_query = getTextareaValue('oql_query');
            }

            if (widgetType === 'summary_count') {
                widgetData.api_metric = getInputValue('api_metric');
            }

            if (widgetType === 'oql_chart') {
                widgetData.chart_type = getSelectValue('chart_type');
            }

            newLayout.push(widgetData as WidgetConfig);
        });

        try {
            const response = await fetch('/api/dashboard_layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newLayout)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server failed to save layout.');
            }
            showMessage('Layout saved successfully!', 'success');
            currentLayout = newLayout;
        } catch (error) {
            showMessage(`Error: ${(error as Error).message}`, 'error');
        }
    };

    const showMessage = (msg: string, type: 'info' | 'success' | 'error' = 'info'): void => {
        messageArea.textContent = msg;
        messageArea.className = `message-area ${type}`;
        setTimeout(() => { messageArea.className = 'hidden'; }, 3000);
    };

    initEditor();
});
