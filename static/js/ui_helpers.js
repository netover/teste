/**
 * A callback function for modal setup.
 * @param {HTMLElement} modalContent - The main content element of the modal.
 * @param {() => void} closeModal - A function to programmatically close the modal.
 */
// type ModalSetupCallback = (modalContent: HTMLElement, closeModal: () => void) => void;

/**
 * Creates and displays a generic, draggable modal window.
 * @param {string} title - The title to display in the modal header.
 * @param {string} bodyHTML - The HTML content to display in the modal body.
 * @param {Function} [setupCallback] - An optional callback function that receives the modal content element for further setup.
 */
export function createModal(title, bodyHTML, setupCallback) {
    // Remove existing modal first
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';

    const content = document.createElement('div');
    content.className = 'modal-content';

    const titleEl = document.createElement('h2');
    titleEl.className = 'modal-title';
    titleEl.textContent = title;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close-btn';
    closeBtn.innerHTML = '&times;';

    const body = document.createElement('div');
    body.className = 'modal-body';
    body.innerHTML = bodyHTML;

    content.append(closeBtn, titleEl, body);
    overlay.appendChild(content);
    document.body.appendChild(overlay);

    requestAnimationFrame(() => {
        overlay.classList.add('visible');
        content.classList.add('animated-open');
    });

    const closeModal = () => {
        content.classList.remove('animated-open');
        setTimeout(() => {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        }, 300);
    };

    closeBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    let isDragging = false;
    let offset = { x: 0, y: 0 };
    titleEl.style.cursor = 'grab';

    const onMouseDown = (e) => {
        isDragging = true;
        offset = { x: e.clientX - content.offsetLeft, y: e.clientY - content.offsetTop };
        titleEl.style.cursor = 'grabbing';
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    };

    const onMouseMove = (e) => {
        if (!isDragging) return;
        e.preventDefault();
        content.style.transform = 'none';
        content.style.left = `${e.clientX - offset.x}px`;
        content.style.top = `${e.clientY - offset.y}px`;
    };

    const onMouseUp = () => {
        isDragging = false;
        titleEl.style.cursor = 'grab';
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
    };

    titleEl.addEventListener('mousedown', onMouseDown);

    if (typeof setupCallback === 'function') {
        setupCallback(content, closeModal);
    }
}

export function createListWindow(title, itemList, renderItem) {
    let listHtml = '<ul>';
    if (itemList && itemList.length > 0) {
        itemList.forEach(item => { listHtml += renderItem(item); });
    } else {
        listHtml += `<li>No items to display in this category.</li>`;
    }
    listHtml += '</ul>';
    createModal(title, listHtml);
}

export function createJobDetailWindow(jobStream) {
    const { jobStreamName, workstationName, status, startTime, id: jobId } = jobStream;
    const planId = 'current';

    const getStatusClass = (status) => {
        if (!status) return 'status-unknown';
        const s = status.toLowerCase();
        if (s.includes('succ') || s.includes('link')) return 'status-success';
        if (s.includes('error') || s.includes('abend')) return 'status-error';
        if (s.includes('exec')) return 'status-running';
        if (s.includes('pend')) return 'status-pending';
        return 'status-unknown';
    };

    const bodyHTML = `
        <p><strong>Name:</strong> ${jobStreamName}</p>
        <p><strong>Workstation:</strong> ${workstationName}</p>
        <p><strong>Status:</strong> <span class="status-badge ${getStatusClass(status)}">${status}</span></p>
        <p><strong>Start Time:</strong> ${startTime ? new Date(startTime).toLocaleString() : 'N/A'}</p>
        <div class="modal-footer">
            <button class="btn btn-secondary" data-action="rerun">Rerun</button>
            <button class="btn btn-warning" data-action="hold">Hold</button>
            <button class="btn btn-info" data-action="release">Release</button>
            <button class="btn btn-danger" data-action="cancel">Cancel</button>
        </div>
    `;

    createModal(`Job Details: ${jobStreamName}`, bodyHTML, (modal, closeModal) => {
        modal.querySelectorAll('.modal-footer button').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (confirm(`Are you sure you want to ${action} job "${jobStreamName}"?`)) {
                    // Dispatch a custom event instead of handling the fetch here
                    const event = new CustomEvent('job-action', {
                        detail: { planId, jobId, action, jobName: jobStreamName, closeModal }
                    });
                    document.dispatchEvent(event);
                }
            });
        });
    });
}
