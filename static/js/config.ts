import '../css/style.css';

/**
 * JavaScript file for the Configuration page.
 * Handles loading the current configuration from the backend,
 * populating the form, and submitting changes back to the backend.
 */
interface AppConfig {
    hostname: string;
    port: string;
    username: string;
    verify_ssl: string; // This is 'true' or 'false' from the backend
}

document.addEventListener('DOMContentLoaded', () => {
    // DOM Element References
    const form = document.getElementById('config-form') as HTMLFormElement;
    const statusDiv = document.getElementById('message-area') as HTMLElement;
    const hostnameInput = document.getElementById('hostname') as HTMLInputElement;
    const portInput = document.getElementById('port') as HTMLInputElement;
    const usernameInput = document.getElementById('username') as HTMLInputElement;
    const verifySslInput = document.getElementById('verify_ssl') as HTMLInputElement;

    /**
     * Fetches the current configuration from the backend API and populates the form fields.
     */
    const loadConfig = async (): Promise<void> => {
        try {
            const response = await fetch('/api/config');
            const config: AppConfig = await response.json();

            if (config) {
                hostnameInput.value = config.hostname || '';
                portInput.value = config.port || '';
                usernameInput.value = config.username || '';
                verifySslInput.checked = (config.verify_ssl === 'true');
            }
        } catch (error) {
            showStatus('Failed to load current configuration.', 'error');
            console.error("Error loading config:", error);
        }
    };

    /**
     * Handles the form submission event.
     */
    form.addEventListener('submit', async (event: SubmitEvent) => {
        event.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries()) as Record<string, any>;
        data.verify_ssl = verifySslInput.checked;

        if (!data.password) {
            delete data.password;
        }

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (response.ok) {
                showStatus(result.success, 'success');
            } else {
                throw new Error(result.detail || 'An unknown error occurred.');
            }
        } catch (error) {
            showStatus((error as Error).message, 'error');
            console.error("Error saving config:", error);
        }
    });

    /**
     * Displays a status message to the user.
     * @param message The message to display.
     * @param type The type of message ('success' or 'error'), used for styling.
     */
    const showStatus = (message: string, type: 'success' | 'error'): void => {
        if (!statusDiv) return;
        statusDiv.textContent = message;
        statusDiv.className = `message-area ${type}`;

        setTimeout(() => {
            statusDiv.className = 'hidden';
        }, 5000);
    };

    loadConfig();
});
