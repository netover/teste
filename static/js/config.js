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

        // The password field is only sent if the user types something in it.
        // If it's empty, we don't include it in the payload.
        // A more robust solution would be needed if we wanted to allow clearing the password.
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

        // Hide the message after 5 seconds
        setTimeout(() => {
            statusDiv.className = '';
        }, 5000);
    };

    // Initial load
    loadConfig();
});
