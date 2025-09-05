document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('config-form');
    const statusDiv = document.getElementById('save-status');

    // Load current configuration when the page loads
    const loadConfig = async () => {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();

            if (config) {
                document.getElementById('hostname').value = config.hostname || '';
                document.getElementById('port').value = config.port || '';
                document.getElementById('username').value = config.username || '';
                // Don't populate the password field for security
                document.getElementById('verify_ssl').checked = (config.verify_ssl === 'true');
            }
        } catch (error) {
            showStatus('Failed to load configuration.', 'error');
        }
    };

    // Handle form submission
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Handle checkbox value, since unchecked boxes are not included in FormData
        data.verify_ssl = document.getElementById('verify_ssl').checked;

        if (!data.password) {
            delete data.password;
        }

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (response.ok) {
                showStatus(result.success, 'success');
            } else {
                throw new Error(result.error || 'Failed to save configuration.');
            }
        } catch (error) {
            showStatus(error.message, 'error');
        }
    });

    const showStatus = (message, type) => {
        statusDiv.textContent = message;
        statusDiv.className = type; // 'success' or 'error'

        setTimeout(() => {
            statusDiv.className = '';
        }, 5000);
    };

    // Initial load
    loadConfig();
});
