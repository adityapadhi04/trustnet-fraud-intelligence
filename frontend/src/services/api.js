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
