/**
 * Real-time Monitoring via WebSocket
 *
 * This script connects to the backend WebSocket server to receive and display
 * real-time job status updates and alerts.
 */
export class RealtimeMonitoring {
    constructor(wsUrl, maxReconnectAttempts = 5, initialReconnectDelay = 1000) {
        this.wsUrl = wsUrl;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = maxReconnectAttempts;
        this.reconnectDelay = initialReconnectDelay;
        this.initialReconnectDelay = initialReconnectDelay;
    }

    /**
     * Generates a simple unique ID for the WebSocket session.
     * @returns {string} A unique identifier.
     */
    generateUserId() {
        return `user_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }

    /**
     * Connects to the WebSocket server.
     */
    connect() {
        const userId = this.generateUserId();
        const fullWsUrl = `${this.wsUrl}/${userId}`;

        console.log(`Attempting to connect to WebSocket: ${fullWsUrl}`);
        this.socket = new WebSocket(fullWsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connection established.');
            this.reconnectAttempts = 0;
            this.reconnectDelay = this.initialReconnectDelay;
            this.showConnectionStatus('connected');
            // Dispatch a custom event to notify other scripts
            document.dispatchEvent(new CustomEvent('websocket:connected'));
        };

        this.socket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleRealtimeUpdate(message);
            } catch (error) {
                console.error('Error parsing incoming WebSocket message:', error);
            }
        };

        this.socket.onclose = () => {
            console.warn('WebSocket connection closed.');
            this.showConnectionStatus('disconnected');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionStatus('error');
            // The onclose event will be triggered next, which handles reconnection.
        };
    }

    /**
     * Handles incoming messages from the WebSocket.
     * @param {object} message The parsed message from the server.
     */
    handleRealtimeUpdate(message) {
        console.debug('Received update:', message);
        switch (message.type) {
            case 'job_status_update':
                this.updateJobStatus(message.data);
                break;
            case 'alert_notification':
                this.showAlert(message.data);
                break;
            // Add cases for other message types like 'prediction_update' in the future
            default:
                console.log('Received unhandled message type:', message.type);
        }
    }

    /**
     * Updates the status of a job on the dashboard.
     * @param {object} jobData The job data from the server.
     */
    updateJobStatus(jobData) {
        // The job cards are in the #job-streams-grid container
        const jobCard = document.querySelector(`#job-streams-grid [data-job-name="${jobData.job_name}"]`);

        if (jobCard) {
            const statusElement = jobCard.querySelector('.status-badge');
            if (statusElement) {
                statusElement.textContent = jobData.new_status;
                // Update the class to change the color, e.g., status-abend, status-exec
                statusElement.className = `status-badge status-${jobData.new_status.toLowerCase()}`;

                // Add a visual indicator for the change
                jobCard.classList.add('fade-in');
                setTimeout(() => jobCard.classList.remove('fade-in'), 1500);
            }
        } else {
            // If the job card doesn't exist, it might be a new job.
            // The main.js polling will likely pick it up, or this could be extended
            // to dynamically add new job cards.
            console.log(`Job card for ${jobData.job_name} not found. A page refresh might be needed to see new jobs.`);
        }
    }

    /**
     * Displays a real-time alert message.
     * @param {object} alertData The alert data from the server.
     */
    showAlert(alertData) {
        const alertsContainer = document.getElementById('alerts-container');
        if (!alertsContainer) {
            console.error('Alerts container not found.');
            return;
        }

        const alertEl = document.createElement('div');
        alertEl.className = `alert alert-${alertData.severity.toLowerCase()}`;

        const titleEl = document.createElement('strong');
        titleEl.textContent = `${alertData.title}: `;

        const messageEl = document.createElement('span');
        messageEl.textContent = alertData.message;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'close-btn';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = () => alertEl.remove();

        alertEl.appendChild(titleEl);
        alertEl.appendChild(messageEl);
        alertEl.appendChild(closeBtn);

        alertsContainer.prepend(alertEl);

        // Automatically remove the alert after some time
        setTimeout(() => {
            alertEl.style.opacity = '0';
            setTimeout(() => alertEl.remove(), 500);
        }, 10000);
    }

    /**
     * Manages reconnection attempts with exponential backoff.
     */
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect in ${this.reconnectDelay / 1000}s (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);

            // Exponential backoff
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max delay 30s
        } else {
            console.error('Max WebSocket reconnection attempts reached.');
        }
    }

    /**
     * Displays the current WebSocket connection status to the user.
     * @param {string} status 'connected', 'disconnected', or 'error'.
     */
    showConnectionStatus(status) {
        let indicator = document.getElementById('ws-status-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'ws-status-indicator';
            document.body.appendChild(indicator);
        }

        indicator.className = `ws-status-indicator status-${status}`;
        indicator.title = `WebSocket: ${status.charAt(0).toUpperCase() + status.slice(1)}`;
    }
}
