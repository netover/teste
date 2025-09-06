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
function createModal(title, bodyHTML, setupCallback) {
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

    // --- Animation and Closing Logic ---
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
            // Clean up the drag listeners
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        }, 300);
    };

    closeBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    // --- Dragging Logic ---
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
