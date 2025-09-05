/**
 * JavaScript file for the Configuration page.
 * Handles loading the current configuration from the backend,
 * populating the form, and submitting changes back to the backend.
 */
document.addEventListener('DOMContentLoaded', () => {
    // DOM Element References
    const form = document.getElementById('config-form');
    const statusDiv = document.getElementById('save-status');

    /**
     * Fetches the current configuration from the backend API and populates the form fields.
     */
    const loadConfig = async () => {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();

            if (config) {
                document.getElementById('hostname').value = config.hostname || '';
                document.getElementById('port').value = config.port || '';
                document.getElementById('username').value = config.username || '';
                // The 'verify_ssl' value is a string 'true' or 'false' from the config parser
                document.getElementById('verify_ssl').checked = (config.verify_ssl === 'true');
                // For security, the password field is intentionally not populated.
            }
        } catch (error) {
            showStatus('Failed to load current configuration.', 'error');
            console.error("Error loading config:", error);
        }
    };

    /**
     * Handles the form submission event.
     * It gathers form data and sends it to the backend to be saved.
     */
    form.addEventListener('submit', async (event) => {
        // Prevent the default browser form submission (which causes a page reload).
        event.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // FormData doesn't include unchecked checkboxes, so we read its state directly.
        data.verify_ssl = document.getElementById('verify_ssl').checked;

        // For security, only send the password if the user has entered a new one.
        // The backend logic is designed to preserve the old password if this field is omitted.
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
                throw new Error(result.error || 'An unknown error occurred.');
            }
        } catch (error) {
            showStatus(error.message, 'error');
            console.error("Error saving config:", error);
        }
    });

    /**
     * Displays a status message (e.g., "Saved successfully") to the user.
     * @param {string} message - The message to display.
     * @param {string} type - The type of message ('success' or 'error'), used for styling.
     */
    const showStatus = (message, type) => {
        statusDiv.textContent = message;
        statusDiv.className = type; // Add class for styling

        // Hide the message after 5 seconds for a better user experience.
        setTimeout(() => {
            statusDiv.className = '';
        }, 5000);
    };

    // Load the configuration as soon as the page is ready.
    loadConfig();
});
