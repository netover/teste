document.addEventListener('DOMContentLoaded', () => {
    const editorContainer = document.getElementById('editor-container');
    const messageArea = document.createElement('div');
    messageArea.id = 'message-area';
    messageArea.className = 'hidden';
    let widgetListContainer;
    let sortableInstance;

    let currentLayout = [];


    const loadLayout = async () => {
        try {
            const response = await fetch('/api/dashboard_layout');
            if (!response.ok) throw new Error('Could not load layout.');
            currentLayout = await response.json();
            renderWidgetList();
        } catch (error) {
            showMessage(`Error: ${error.message}`, 'error');
        }
    };

    const renderWidgetList = () => {
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

    const createWidgetEditorElement = (widget) => {
        const el = document.createElement('div');
        el.className = 'widget-editor-item';
        el.dataset.widgetId = widget.id;
        el.dataset.widgetType = widget.type || 'summary_count';

        let fieldsHTML = '';
        if (el.dataset.widgetType === 'oql_table') {
            fieldsHTML = `
                <h4>OQL Table Widget</h4>
                <div class="form-group">
                    <label>Title:</label>
                    <input type="text" name="title" value="${widget.title || ''}">
                </div>
                <div class="form-group">
                    <label>Query Source:</label>
                    <select name="oql_source">
                        <option value="plan" ${widget.oql_source === 'plan' ? 'selected' : ''}>Plan (Live)</option>
                        <option value="model" ${widget.oql_source === 'model' ? 'selected' : ''}>Model (Database)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>OQL Query:</label>
                    <textarea name="oql_query" rows="4">${widget.oql_query || ''}</textarea>
                    <div class="validate-container">
                        <button class="btn btn-secondary validate-oql-btn">Validate Query</button>
                        <span class="validate-result"></span>
                    </div>
                </div>
            `;
        } else if (el.dataset.widgetType === 'oql_chart') {
            fieldsHTML = `
                <h4>OQL Chart Widget</h4>
                <div class="form-group">
                    <label>Title:</label>
                    <input type="text" name="title" value="${widget.title || ''}">
                </div>
                <div class="form-group">
                    <label>Chart Type:</label>
                    <select name="chart_type">
                        <option value="bar" ${widget.chart_type === 'bar' ? 'selected' : ''}>Bar Chart</option>
                        <option value="pie" ${widget.chart_type === 'pie' ? 'selected' : ''}>Pie Chart</option>
                        <option value="doughnut" ${widget.chart_type === 'doughnut' ? 'selected' : ''}>Doughnut Chart</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Query Source:</label>
                    <select name="oql_source">
                        <option value="plan" ${widget.oql_source === 'plan' ? 'selected' : ''}>Plan (Live)</option>
                        <option value="model" ${widget.oql_source === 'model' ? 'selected' : ''}>Model (Database)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Label Column:</label>
                    <input type="text" name="label_column" value="${widget.label_column || ''}" placeholder="e.g., status">
                </div>
                <div class="form-group">
                    <label>Data Column:</label>
                    <input type="text" name="data_column" value="${widget.data_column || ''}" placeholder="e.g., count">
                </div>
                <div class="form-group">
                    <label>OQL Query:</label>
                    <textarea name="oql_query" rows="4">${widget.oql_query || ''}</textarea>
                    <div class="validate-container">
                        <button class="btn btn-secondary validate-oql-btn">Validate Query</button>
                        <span class="validate-result"></span>
                    </div>
                </div>
            `;
        } else { // Default to summary_count
            fieldsHTML = `
                <h4>Summary Count Widget</h4>
                <div class="form-group">
                    <label>Label:</label>
                    <input type="text" name="label" value="${widget.label || ''}">
                </div>
                <div class="form-group">
                    <label>Icon (Font Awesome):</label>
                    <input type="text" name="icon" value="${widget.icon || ''}">
                </div>
                <div class="form-group">
                    <label>Color Class:</label>
                    <input type="text" name="color_class" value="${widget.color_class || ''}">
                </div>
                <div class="form-group">
                    <label>API Metric:</label>
                    <input type="text" name="api_metric" value="${widget.api_metric || ''}">
                </div>
            `;
        }

        el.innerHTML = `
            ${fieldsHTML}
            <button class="remove-widget-btn btn-danger"><i class="fas fa-trash"></i></button>
        `;

        el.querySelector('.remove-widget-btn').addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to remove this widget?')) {
                const widgetIdToRemove = el.dataset.widgetId;
                currentLayout = currentLayout.filter(w => w.id !== widgetIdToRemove);
                el.remove();
            }
        });

        // Add event listener for the validate button if it exists
        const validateBtn = el.querySelector('.validate-oql-btn');
        if (validateBtn) {
            validateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const textarea = el.querySelector('textarea[name="oql_query"]');
                const resultSpan = el.querySelector('.validate-result');
                validateOQLQuery(textarea.value, resultSpan);
            });
        }

        return el;
    };

    const validateOQLQuery = async (query, resultSpan) => {
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
            resultSpan.textContent = `✗ Invalid query: ${error.message}`;
            resultSpan.className = 'validate-result error';
        }
    };

    const initSortable = () => {
        if (sortableInstance) {
            sortableInstance.destroy();
        }
        sortableInstance = new Sortable(widgetListContainer, {
            animation: 150,
            handle: '.widget-editor-item',
            ghostClass: 'widget-ghost',
            onEnd: () => {
                const newOrder = Array.from(widgetListContainer.children).map(item => item.dataset.widgetId);
                currentLayout.sort((a, b) => newOrder.indexOf(a.id) - newOrder.indexOf(b.id));
            }
        });
    };



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
            <div class="modal-actions">
                <button id="create-widget-btn" class="btn btn-primary">Create</button>
            </div>
        `;

        const setupCallback = (modalContent, closeModal) => {
            const createBtn = modalContent.querySelector('#create-widget-btn');
            const typeSelect = modalContent.querySelector('#widget-type-select');

            createBtn.addEventListener('click', () => {
                const widgetType = typeSelect.value;
                const newWidget = {
                    id: `widget_${new Date().getTime()}`, // Simple unique ID
                    type: widgetType
                };

                // Add default properties based on type
                if (widgetType === 'summary_count') {
                    newWidget.label = "New Summary";
                    newWidget.icon = "fas fa-info-circle";
                    newWidget.api_metric = "some_metric";
                    newWidget.color_class = "color-gray";
                } else if (widgetType === 'oql_table') {
                    newWidget.title = "New OQL Table";
                    newWidget.oql_source = "plan";
                    newWidget.oql_query = "SHOW JOBS";
                } else if (widgetType === 'oql_chart') {
                    newWidget.title = "New OQL Chart";
                    newWidget.chart_type = "bar";
                    newWidget.oql_source = "plan";
                    newWidget.label_column = "status";
                    newWidget.data_column = "count";
                    newWidget.oql_query = "SHOW JOBS | GROUP BY status";
                }

                currentLayout.push(newWidget);
                renderWidgetList();
                closeModal();
            });
        };

        createModal('Add New Widget', modalHTML, setupCallback);
    };

    // Replace the direct call to addWidget with the modal opener
    const initEditor = () => {
        editorContainer.innerHTML = `
            <h2>Edit Your Dashboard Layout</h2>
            <div id="widget-list" class="widget-editor-list"></div>
            <div class="editor-actions">
                <button id="add-widget-btn" class="btn">Add New Widget</button>
                <button id="save-layout-btn" class="btn btn-primary">Save Layout</button>
            </div>
        `;
        editorContainer.appendChild(messageArea);
        widgetListContainer = document.getElementById('widget-list');

        // The button now calls the modal function instead of addWidget directly
        document.getElementById('add-widget-btn').addEventListener('click', showAddWidgetModal);
        document.getElementById('save-layout-btn').addEventListener('click', saveLayout);

        loadLayout();
    };

    const saveLayout = async () => {
        const newLayout = [];
        const widgetItems = widgetListContainer.querySelectorAll('.widget-editor-item');

        widgetItems.forEach(item => {
            const widgetId = item.dataset.widgetId;
            const widgetType = item.dataset.widgetType;
            const originalData = currentLayout.find(w => w.id === widgetId) || {};

            let widgetData = { id: widgetId, type: widgetType };

            if (widgetType === 'oql_table') {
                widgetData.title = item.querySelector('[name="title"]').value;
                widgetData.oql_source = item.querySelector('[name="oql_source"]').value;
                widgetData.oql_query = item.querySelector('[name="oql_query"]').value;
            } else if (widgetType === 'oql_chart') {
                widgetData.title = item.querySelector('[name="title"]').value;
                widgetData.chart_type = item.querySelector('[name="chart_type"]').value;
                widgetData.oql_source = item.querySelector('[name="oql_source"]').value;
                widgetData.label_column = item.querySelector('[name="label_column"]').value;
                widgetData.data_column = item.querySelector('[name="data_column"]').value;
                widgetData.oql_query = item.querySelector('[name="oql_query"]').value;
            } else {
                widgetData.label = item.querySelector('[name="label"]').value;
                widgetData.icon = item.querySelector('[name="icon"]').value;
                widgetData.color_class = item.querySelector('[name="color_class"]').value;
                widgetData.api_metric = item.querySelector('[name="api_metric"]').value;
                // Preserve modal data for summary widgets
                widgetData.modal_data_key = originalData.modal_data_key;
                widgetData.modal_title = originalData.modal_title;
                widgetData.modal_item_renderer = originalData.modal_item_renderer;
            }
            newLayout.push(widgetData);
        });

        try {
            const response = await fetch('/api/dashboard_layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newLayout)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Server failed to save layout.');
            }
            showMessage('Layout saved successfully!', 'success');
            currentLayout = newLayout;
        } catch (error) {
            showMessage(`Error: ${error.message}`, 'error');
        }
    };

    const showMessage = (msg, type = 'info') => {
        messageArea.textContent = msg;
        messageArea.className = `message-area ${type}`;
        setTimeout(() => { messageArea.className = 'hidden'; }, 3000);
    };

    initEditor();
});
