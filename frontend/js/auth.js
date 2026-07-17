// core/auth.js
import api from './api.js';

const auth = {
    login: async (username, password) => {
        // We use the exact payload format your FastAPI backend expects
        const data = await api.post('/auth/login', {
            username: username,
            password: password,
            role: "Student", // Sent to satisfy schema requirements if needed
            name: "User"
        });

        // 1. Save the token
        localStorage.setItem('token', data.access_token);

        // 2. Decode the JWT to find out if they are a Manager, Professor, or Student
        try {
            const payload = JSON.parse(atob(data.access_token.split('.')[1]));
            const role = payload.role.toLowerCase();
            
            // Save for routing guards
            localStorage.setItem('user_role', role);
            
            // Save for main.js UI rendering
            localStorage.setItem('userRole', role);
            localStorage.setItem('userName', payload.sub); // 'sub' contains the username from FastAPI            
            // 3. Route them to the correct page
            auth.redirectToDashboard(role);
        } catch (e) {
            throw new Error("توکن نامعتبر است (Invalid Token)");
        }
    },
   logout: () => {
        // 1. Destroy the session data
        localStorage.removeItem('token');
        localStorage.removeItem('user_role');
        
        // 2. Redirect back to the root login page
        window.location.href = '/index.html';
    },
redirectToDashboard: (role) => {
        if (role === 'manager' || role === 'admin') {
            window.location.href = '/pages/admin/dashboard.html'; 
        } else if (role === 'professor') {
            window.location.href = '/pages/professor/dashboard.html';
        } else {
            window.location.href = '/pages/student/dashboard.html';
        }
    },
   
    checkPageGuard: (allowedRoles) => {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('user_role');

        // If they have no token, or their role isn't allowed on this HTML page, kick them out
        if (!token || !role || !allowedRoles.includes(role)) {
            localStorage.removeItem('token');
            localStorage.removeItem('user_role');
            window.location.href = '/index.html';
        }
    }
};

export default auth;

