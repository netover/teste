document.addEventListener('DOMContentLoaded', () => {
    const editorContainer = document.getElementById('editor-container');
    const messageArea = document.createElement('div');
    messageArea.id = 'message-area';
    messageArea.className = 'hidden';
    let widgetListContainer;
    let sortableInstance;

    let currentLayout = [];

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

        document.getElementById('add-widget-btn').addEventListener('click', addWidget);
        document.getElementById('save-layout-btn').addEventListener('click', saveLayout);

        loadLayout();
    };

    const loadLayout = async () => {
        console.log("Loading layout...");
        try {
            const response = await fetch('/api/dashboard_layout');
            console.log("Layout response:", response.status);
            if (!response.ok) throw new Error('Could not load layout.');
            currentLayout = await response.json();
            console.log("Layout data:", currentLayout);
            renderWidgetList();
        } catch (error) {
            console.error("Error loading layout:", error);
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

        el.innerHTML = `
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
        return el;
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

    const addWidget = () => {
        if (widgetListContainer.querySelector('p')) {
            widgetListContainer.innerHTML = '';
        }
        const newWidgetData = {
            id: `widget-${Date.now()}`,
            label: "New Widget",
            icon: "fas fa-plus-circle",
            color_class: "color-gray",
            api_metric: ""
        };
        currentLayout.push(newWidgetData);
        const widgetEl = createWidgetEditorElement(newWidgetData);
        widgetListContainer.appendChild(widgetEl);
    };

    const saveLayout = async () => {
        const newLayout = [];
        const widgetItems = widgetListContainer.querySelectorAll('.widget-editor-item');

        widgetItems.forEach(item => {
            const widgetId = item.dataset.widgetId;
            const originalData = currentLayout.find(w => w.id === widgetId) || {};
            newLayout.push({
                id: widgetId,
                label: item.querySelector('[name="label"]').value,
                icon: item.querySelector('[name="icon"]').value,
                color_class: item.querySelector('[name="color_class"]').value,
                api_metric: item.querySelector('[name="api_metric"]').value,
                type: originalData.type || 'summary_count',
                modal_data_key: originalData.modal_data_key,
                modal_title: originalData.modal_title,
                modal_item_renderer: originalData.modal_item_renderer,
            });
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
