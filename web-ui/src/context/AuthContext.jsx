import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { jwtDecode } from "jwt-decode";
import { GoogleOAuthProvider } from '@react-oauth/google';

const AuthContext = createContext(null);

// Replace with your actual Google Client ID from console.cloud.google.com
// For dev, it might come from .env, but Vite exposes env via import.meta.env
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "YOUR_GOOGLE_CLIENT_ID_HERE";

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check local storage for token
        const token = localStorage.getItem('token');
        if (token) {
            try {
                const decoded = jwtDecode(token);
                // Check expiry
                if (decoded.exp * 1000 < Date.now()) {
                    logout();
                } else {
                    // Set user from token or fetch profile
                    // For now, just use token info
                    setUser({ ...decoded, ...JSON.parse(localStorage.getItem('user_data') || '{}') });
                    // Setup axios default
                    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                }
            } catch (e) {
                logout();
            }
        }
        setLoading(false);
    }, []);

    const login = (token, userData) => {
        localStorage.setItem('token', token);
        localStorage.setItem('user_data', JSON.stringify(userData));
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        setUser(userData);
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user_data');
        delete axios.defaults.headers.common['Authorization'];
        setUser(null);
    };

    const googleLogin = async (credentialResponse) => {
        try {
            const res = await axios.post('/api/auth/google', { token: credentialResponse.credential });
            login(res.data.access_token, res.data.user);
            return true;
        } catch (err) {
            console.error("Google Login Failed", err);
            return false;
        }
    };

    return (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <AuthContext.Provider value={{ user, login, logout, googleLogin, loading }}>
                {!loading && children}
            </AuthContext.Provider>
        </GoogleOAuthProvider>
    );
};

export const useAuth = () => useContext(AuthContext);
