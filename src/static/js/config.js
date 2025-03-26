// API Configuration
const API_URL = 'https://lokiplus-api.onrender.com';

// API Endpoints
const API_ENDPOINTS = {
    health: `${API_URL}/health`,
    healthDatabase: `${API_URL}/health/database`,
    healthLive: `${API_URL}/health/live`,
    accounts: `${API_URL}/accounts`,
    clients: `${API_URL}/clients`,
    accountClients: `${API_URL}/account-clients`
};

// Status check configuration
const STATUS_CHECK_INTERVAL = 30000; // 30 seconds

// Export configuration
window.API_CONFIG = {
    BASE_URL: API_URL,
    ENDPOINTS: API_ENDPOINTS,
    STATUS_CHECK_INTERVAL
}; 