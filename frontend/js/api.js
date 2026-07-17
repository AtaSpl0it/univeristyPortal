// core/api.js

// Change this to your public IP if accessing from outside localhost
const BASE_URL = 'http://176.124.204.33:3000/api'; 

async function request(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // If the user is logged in, inject the secure JWT token into the header
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'خطا در ارتباط با سرور (Server Error)');
    }

    return response.json();
}

export default {
    get: (endpoint) => request(endpoint),
    post: (endpoint, body) => request(endpoint, { method: 'POST', body: JSON.stringify(body) })
};
