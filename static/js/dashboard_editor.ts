import Sortable from 'sortablejs';
import { createModal } from './ui_helpers.js';
import '../css/style.css';

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
        if (el.dataset.widgetType === 'oql_table') {
            fieldsHTML = `...`; // Omitted for brevity, same as original
        } else if (el.dataset.widgetType === 'oql_chart') {
            fieldsHTML = `...`; // Omitted for brevity, same as original
        } else {
            fieldsHTML = `...`; // Omitted for brevity, same as original
        }

        el.innerHTML = `
            ${fieldsHTML}
            <button class="remove-widget-btn btn-danger"><i class="fas fa-trash"></i></button>
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
        const modalHTML = `...`; // Omitted for brevity
        const setupCallback = (modalContent: HTMLElement, closeModal: () => void) => {
            const createBtn = modalContent.querySelector<HTMLButtonElement>('#create-widget-btn');
            const typeSelect = modalContent.querySelector<HTMLSelectElement>('#widget-type-select');

            createBtn?.addEventListener('click', () => {
                if (!typeSelect) return;
                const widgetType: WidgetType = typeSelect.value as WidgetType;
                const newWidget: Partial<WidgetConfig> = {
                    id: `widget_${new Date().getTime()}`,
                    type: widgetType
                };

                if (widgetType === 'summary_count') {
                    newWidget.label = "New Summary";
                } // ... other types

                currentLayout.push(newWidget as WidgetConfig);
                renderWidgetList();
                closeModal();
            });
        };
        createModal('Add New Widget', modalHTML, setupCallback);
    };

    const initEditor = (): void => {
        editorContainer.innerHTML = `...`; // Omitted
        editorContainer.appendChild(messageArea);
        widgetListContainer = document.getElementById('widget-list') as HTMLElement;

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
            const originalData = currentLayout.find(w => w.id === widgetId) || {};

            let widgetData: Partial<WidgetConfig> = { id: widgetId, type: widgetType };

            if (widgetType === 'oql_table') {
                // ...
            } else if (widgetType === 'oql_chart') {
                // ...
            } else {
                // ...
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
