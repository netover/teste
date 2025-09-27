import Sortable from 'sortablejs';
import { createModal, showMessage } from './ui_helpers';
import '../css/style.css';

// --- Type Definitions ---
interface WidgetConfig {
    id: string;
    type: string;
    [key: string]: any;
}

type WidgetType = 'summary_count' | 'oql_table' | 'oql_chart';

// --- Main Application Logic ---
document.addEventListener('DOMContentLoaded', () => {
    const editorContainer = document.getElementById('editor-container');
    if (!editorContainer) return;

    const messageArea = document.createElement('div');
    messageArea.id = 'message-area';
    let widgetListContainer: HTMLElement;
    let sortableInstance: Sortable;

    let currentLayout: WidgetConfig[] = [];

    // Fetches the current layout from the backend.
    const loadLayout = async () => {
        try {
            const response = await fetch('/api/layout');
            if (!response.ok) throw new Error('Could not load layout.');
            currentLayout = await response.json();
            renderWidgetList();
        } catch (error) {
            showMessage(`Error loading layout: ${(error as Error).message}`, 'error', editorContainer);
        }
    };

    // Renders the list of widget editors based on the currentLayout data.
    const renderWidgetList = () => {
        widgetListContainer.innerHTML = '';
        if (currentLayout.length === 0) {
            widgetListContainer.innerHTML = '<p class="text-center p-4">No widgets defined. Add one to get started!</p>';
        } else {
            currentLayout.forEach((widget) => {
                const widgetEl = createWidgetEditorElement(widget);
                widgetListContainer.appendChild(widgetEl);
            });
        }
        initSortable();
    };

    // Creates the DOM element for a single widget editor.
    const createWidgetEditorElement = (widget: WidgetConfig): HTMLElement => {
        const el = document.createElement('div');
        el.className = 'widget-editor-item';
        el.dataset.widgetId = widget.id;
        el.dataset.widgetType = widget.type;

        // General properties to exclude from automatic field generation
        const excludedKeys = ['id', 'type', 'oql_query', 'chart_type', 'columns'];

        let fieldsHTML = Object.entries(widget)
            .filter(([key]) => !excludedKeys.includes(key))
            .map(([key, value]) => `
                <div class="form-group">
                    <label for="${widget.id}-${key}">${key.replace(/_/g, ' ')}</label>
                    <input type="text" id="${widget.id}-${key}" name="${key}" value="${value || ''}" class="form-control">
                </div>
            `).join('');

        // Add specific fields for complex types
        if (widget.type === 'oql_table' || widget.type === 'oql_chart') {
            fieldsHTML += `
                <div class="form-group">
                    <label for="${widget.id}-oql_query">OQL Query</label>
                    <textarea name="oql_query" class="form-control">${widget.oql_query || ''}</textarea>
                    <button class="btn btn-secondary btn-sm validate-oql-btn">Validate</button>
                    <span class="validate-result"></span>
                </div>`;
        }

        if (widget.type === 'oql_table') {
             fieldsHTML += `
                <div class="form-group">
                    <label for="${widget.id}-columns">Columns (JSON)</label>
                    <textarea name="columns" class="form-control">${JSON.stringify(widget.columns, null, 2)}</textarea>
                </div>`;
        }

        if (widget.type === 'oql_chart') {
            fieldsHTML += `
                <div class="form-group">
                    <label for="${widget.id}-chart_type">Chart Type</label>
                    <select name="chart_type" class="form-control">
                        <option value="bar" ${widget.chart_type === 'bar' ? 'selected' : ''}>Bar</option>
                        <option value="line" ${widget.chart_type === 'line' ? 'selected' : ''}>Line</option>
                        <option value="pie" ${widget.chart_type === 'pie' ? 'selected' : ''}>Pie</option>
                    </select>
                </div>`;
        }

        el.innerHTML = `
            <div class="widget-editor-header">
                <h4>${widget.label || widget.type}</h4>
                <button class="remove-widget-btn btn btn-danger btn-sm"><i class="fas fa-trash"></i></button>
            </div>
            <div class="widget-editor-content">
                ${fieldsHTML}
            </div>
        `;

        // Event listener for the remove button
        el.querySelector<HTMLButtonElement>('.remove-widget-btn')?.addEventListener('click', () => {
            if (confirm('Are you sure you want to remove this widget?')) {
                currentLayout = currentLayout.filter(w => w.id !== widget.id);
                // Re-render the entire list to ensure DOM order matches array order
                renderWidgetList();
            }
        });

        // Event listener for OQL validation
        const validateBtn = el.querySelector<HTMLButtonElement>('.validate-oql-btn');
        if (validateBtn) {
            validateBtn.addEventListener('click', () => {
                const textarea = el.querySelector<HTMLTextAreaElement>('textarea[name="oql_query"]');
                const resultSpan = el.querySelector<HTMLSpanElement>('.validate-result');
                if (textarea && resultSpan) {
                    validateOQLQuery(textarea.value, resultSpan);
                }
            });
        }

        return el;
    };

    // Validates an OQL query against the backend.
    const validateOQLQuery = async (query: string, resultSpan: HTMLElement) => {
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


    // Initializes or re-initializes the sortable list.
    const initSortable = () => {
        if (sortableInstance) {
            sortableInstance.destroy();
        }
        sortableInstance = new Sortable(widgetListContainer, {
            animation: 150,
            ghostClass: 'widget-ghost',
            onEnd: () => {
                const newOrder = Array.from(widgetListContainer.children).map(item => (item as HTMLElement).dataset.widgetId);
                currentLayout.sort((a, b) => newOrder.indexOf(a.id)! - newOrder.indexOf(b.id)!);
            }
        });
    };

    // Shows the modal for adding a new widget.
    const showAddWidgetModal = () => {
        const modalHTML = `
            <div class="form-group">
                <label for="widget-type-select">Select Widget Type:</label>
                <select id="widget-type-select" class="form-control">
                    <option value="summary_count">Summary Count</option>
                    <option value="oql_table">OQL Table</option>
                    <option value="oql_chart">OQL Chart</option>
                </select>
            </div>
            <div class="modal-footer">
                <button id="create-widget-btn" class="btn btn-primary">Create Widget</button>
            </div>
        `;

        const setupCallback = (modalContent: HTMLElement, closeModal: () => void) => {
            const createBtn = modalContent.querySelector<HTMLButtonElement>('#create-widget-btn');
            const typeSelect = modalContent.querySelector<HTMLSelectElement>('#widget-type-select');

            createBtn?.addEventListener('click', () => {
                if (!typeSelect) return;
                const widgetType = typeSelect.value as WidgetType;
                const newWidget: WidgetConfig = {
                    id: `widget_${new Date().getTime()}`,
                    type: widgetType,
                    label: "New Widget"
                };

                // Add default properties for new widgets
                if (widgetType === 'summary_count') {
                    newWidget.icon = "fas fa-info-circle";
                    newWidget.api_metric = "metric_name";
                    newWidget.modal_data_key = "data_key";
                    newWidget.color_class = "color-blue";
                } else if (widgetType === 'oql_table') {
                    newWidget.oql_query = "SELECT NAME, STATUS FROM JOB";
                    newWidget.columns = [{header: "Name", accessor: "NAME"}, {header: "Status", accessor: "STATUS"}];
                } else if (widgetType === 'oql_chart') {
                    newWidget.oql_query = "SELECT STATUS, COUNT(*) AS COUNT FROM JOB GROUP BY STATUS";
                    newWidget.chart_type = "bar";
                }

                currentLayout.push(newWidget);
                renderWidgetList();
                closeModal();
            });
        };
        createModal('Add New Widget', modalHTML, setupCallback);
    };

    // Saves the current layout to the backend.
    const saveLayout = async () => {
        const newLayout = currentLayout.map(widget => {
            const widgetElement = widgetListContainer.querySelector<HTMLElement>(`.widget-editor-item[data-widget-id="${widget.id}"]`);
            if (!widgetElement) {
                return widget; // Should not happen, but safe fallback
            }

            // Start with a copy of all original properties to avoid dropping any data
            const updatedWidget: any = { ...widget };

            // Overwrite properties with current values from the form fields
            const inputs = widgetElement.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input, textarea, select');
            inputs.forEach(input => {
                const name = input.name;
                if (name) {
                    if (name === 'columns') {
                        try {
                            updatedWidget[name] = JSON.parse(input.value);
                        } catch (e) {
                            console.error(`Invalid JSON for 'columns' in widget ${widget.id}`);
                            updatedWidget[name] = []; // Revert to empty array on error
                        }
                    } else {
                        updatedWidget[name] = input.value;
                    }
                }
            });
            return updatedWidget;
        });

        try {
            const response = await fetch('/api/layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newLayout)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server failed to save layout.');
            }
            showMessage('Layout saved successfully!', 'success', editorContainer);
            // Update the main state object with the successfully saved layout
            currentLayout = newLayout;
            // Re-render to ensure the UI is consistent with the saved state
            renderWidgetList();
        } catch (error) {
            showMessage(`Error saving layout: ${(error as Error).message}`, 'error', editorContainer);
        }
    };

    // Initializes the editor.
    const initEditor = () => {
        editorContainer.innerHTML = `
            <div class="editor-controls">
                <button id="add-widget-btn" class="btn btn-primary"><i class="fas fa-plus"></i> Add Widget</button>
                <button id="save-layout-btn" class="btn btn-success"><i class="fas fa-save"></i> Save Layout</button>
            </div>
            <div id="widget-list" class="widget-list-container"></div>
        `;
        editorContainer.prepend(messageArea);
        widgetListContainer = document.getElementById('widget-list') as HTMLElement;

        document.getElementById('add-widget-btn')?.addEventListener('click', showAddWidgetModal);
        document.getElementById('save-layout-btn')?.addEventListener('click', saveLayout);

        loadLayout();
    };

    initEditor();
});
