const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Helper to perform fetch requests with error handling.
 */
async function request(path, options = {}) {
    const url = `${API_BASE_URL}${path}`;
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    try {
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            let errorMessage = `HTTP Error ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorMessage = typeof errorData.detail === 'string' 
                        ? errorData.detail 
                        : JSON.stringify(errorData.detail);
                }
            } catch (jsonErr) {
                // Response is not JSON
            }
            throw new Error(errorMessage);
        }
        return await response.json();
    } catch (err) {
        console.error(`API request failed at ${path}:`, err);
        throw new Error(err.message || 'Unable to connect to TRUSTNET API.');
    }
}

/**
 * Fetch health status of the backend
 */
export async function fetchHealth() {
    return await request('/health');
}

/**
 * Fetch ML models status
 */
export async function fetchModelStatus() {
    return await request('/api/v1/model/status');
}

/**
 * Fetch sample synthetic transactions
 */
export async function fetchSampleTransactions(limit = 10) {
    return await request(`/api/v1/transactions/sample?limit=${limit}`);
}

/**
 * Analyze a transaction's risk profile using model features
 */
export async function analyzeRisk(features) {
    return await request('/api/v1/risk/analyze', {
        method: 'POST',
        body: JSON.stringify(features)
    });
}

/**
 * Retrieve details for a specific transaction ID
 */
export async function fetchTransaction(transactionId) {
    return await request(`/api/v1/transactions/${transactionId}`);
}

/**
 * Retrieve network profile for a specific account ID
 */
export async function fetchAccountNetworkProfile(accountId, beforeTimestamp = null) {
    const query = beforeTimestamp ? `?before_timestamp=${encodeURIComponent(beforeTimestamp)}` : '';
    return await request(`/api/v1/network/${accountId}${query}`);
}

/**
 * Fetch all alerts with optional severity and status filters
 */
export async function fetchAlerts(filters = {}) {
    const params = new URLSearchParams();
    if (filters.severity) params.append('severity', filters.severity);
    if (filters.status) params.append('status', filters.status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return await request(`/api/v1/alerts${query}`);
}

/**
 * Fetch details of a specific alert
 */
export async function fetchAlert(alertId) {
    return await request(`/api/v1/alerts/${alertId}`);
}

/**
 * Update the lifecycle status of an alert
 */
export async function updateAlertStatus(alertId, status) {
    return await request(`/api/v1/alerts/${alertId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status })
    });
}

/**
 * Fetch report dashboard summary statistics
 */
export async function fetchReportSummary() {
    return await request('/api/v1/reports/summary');
}

/**
 * Returns the API download endpoint URL for reports
 */
export function getReportDownloadUrl() {
    return `${API_BASE_URL}/api/v1/reports/download`;
}

/**
 * Fetch the next transaction from the live stream simulator
 */
export async function fetchMonitorNext() {
    return await request('/api/v1/monitor/next');
}

/**
 * Fetch the live monitor aggregate statistics and system status
 */
export async function fetchMonitorStatus() {
    return await request('/api/v1/monitor/status');
}

/**
 * Fetch the current demo mode configuration state
 */
export async function fetchDemoMode() {
    return await request('/api/v1/monitor/demo_mode');
}

/**
 * Toggle the demo mode configuration state
 */
export async function toggleDemoMode(enabled) {
    return await request('/api/v1/monitor/demo_mode', {
        method: 'POST',
        body: JSON.stringify({ demo_mode: enabled })
    });
}
