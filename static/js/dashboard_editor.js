document.addEventListener('DOMContentLoaded', () => {
    const editorContainer = document.getElementById('editor-container');
    const messageArea = document.createElement('div');
    messageArea.id = 'message-area';
    messageArea.className = 'hidden';
    editorContainer.appendChild(messageArea);

    let currentLayout = [];

    const loadLayout = async () => {
        try {
            // We fetch from a dynamic endpoint to ensure we get the latest version
            const response = await fetch('/api/dashboard_layout');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Could not load dashboard layout.');
            }
            currentLayout = await response.json();
            renderEditor();
        } catch (error) {
            showMessage(`Error loading layout: ${error.message}`, 'error');
        }
    };

    const renderEditor = () => {
        // Clear previous content and rebuild
        editorContainer.innerHTML = '';

        const listContainer = document.createElement('div');
        listContainer.id = 'widget-list';
        editorContainer.appendChild(listContainer);

        if (currentLayout.length > 0) {
            currentLayout.forEach((widget, index) => {
                const widgetEl = createWidgetEditorElement(widget, index);
                listContainer.appendChild(widgetEl);
            });
        } else {
            listContainer.innerHTML = '<p>No widgets in this layout. Add one to get started!</p>';
        }

        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'editor-actions';
        actionsContainer.innerHTML = `
            <button id="add-widget-btn" class="btn">Add Widget</button>
            <button id="save-layout-btn" class="btn btn-primary">Save Layout</button>
        `;
        editorContainer.appendChild(actionsContainer);
        editorContainer.appendChild(messageArea); // Re-append message area

        // Re-attach event listeners
        document.getElementById('add-widget-btn').addEventListener('click', addWidget);
        document.getElementById('save-layout-btn').addEventListener('click', saveLayout);
    };

    const createWidgetEditorElement = (widget, index) => {
        const el = document.createElement('div');
        el.className = 'widget-editor-item';
        el.dataset.index = index;

        // Simplified editor for now
        el.innerHTML = `
            <div class="form-group">
                <label>Label:</label>
                <input type="text" name="label" value="${widget.label || ''}" placeholder="e.g., ABEND Jobs">
            </div>
            <div class="form-group">
                <label>Icon (Font Awesome):</label>
                <input type="text" name="icon" value="${widget.icon || ''}" placeholder="e.g., fas fa-times-circle">
            </div>
            <div class="form-group">
                <label>Color Class:</label>
                <input type="text" name="color_class" value="${widget.color_class || ''}" placeholder="e.g., color-red">
            </div>
             <div class="form-group">
                <label>API Metric Name:</label>
                <input type="text" name="api_metric" value="${widget.api_metric || ''}" placeholder="e.g., abend_count">
            </div>
            <button class="remove-widget-btn btn-danger">Remove</button>
        `;
        el.querySelector('.remove-widget-btn').addEventListener('click', () => removeWidget(index));
        return el;
    };

    const addWidget = () => {
        const newWidget = {
            id: `widget-${Date.now()}`,
            label: "New Widget",
            icon: "fas fa-question-circle",
            color_class: "color-gray",
            api_metric: ""
        };
        currentLayout.push(newWidget);
        renderEditor(); // Re-render the editor
    };

    const removeWidget = (indexToRemove) => {
        if (confirm('Are you sure you want to remove this widget?')) {
            currentLayout.splice(indexToRemove, 1);
            renderEditor();
        }
    };

    const saveLayout = async () => {
        const widgetItems = document.querySelectorAll('.widget-editor-item');
        const newLayout = [];
        widgetItems.forEach((item, i) => {
            const originalWidget = currentLayout[i] || {}; // Handle case where item was just added
             newLayout.push({
                id: originalWidget.id || `widget-${Date.now()}-${i}`,
                label: item.querySelector('[name="label"]').value,
                icon: item.querySelector('[name="icon"]').value,
                color_class: item.querySelector('[name="color_class"]').value,
                api_metric: item.querySelector('[name="api_metric"]').value,
                // Preserve non-editable properties
                type: originalWidget.type || 'widget',
                modal_data_key: originalWidget.modal_data_key,
                modal_title: originalWidget.modal_title,
                modal_item_renderer: originalWidget.modal_item_renderer,
            });
        });

        try {
            const response = await fetch('/api/dashboard_layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newLayout)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to save layout.');

            showMessage('Layout saved successfully!', 'success');
            currentLayout = newLayout; // Update state
        } catch (error) {
            showMessage(`Error saving layout: ${error.message}`, 'error');
        }
    };

    const showMessage = (msg, type = 'info') => {
        messageArea.textContent = msg;
        messageArea.className = `message-area ${type}`;
        setTimeout(() => { messageArea.className = 'hidden'; }, 5000);
    };

    loadLayout();
});
