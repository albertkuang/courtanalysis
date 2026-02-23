import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { User, Lock, Mail, ArrowRight, Check } from 'lucide-react';

export const LoginPage = () => {
    const { login, googleLogin } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);
            const res = await axios.post('/api/auth/login', formData);
            login(res.data.access_token, res.data.user);
            navigate('/');
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        }
    };

    return (
        <div className="min-h-screen bg-tennis-dark flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-8 shadow-2xl animate-in fade-in zoom-in-95 duration-300">
                <h1 className="text-2xl font-bold text-white mb-2 text-center">Welcome Back</h1>
                <p className="text-slate-400 text-sm text-center mb-8">Sign in to access CourtSide Analytics</p>

                {error && <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs p-3 rounded-lg mb-4 text-center">{error}</div>}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-500 uppercase">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                            <input
                                type="email" required
                                value={email} onChange={e => setEmail(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white text-sm focus:border-tennis-blue focus:outline-none"
                                placeholder="name@example.com"
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-500 uppercase">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                            <input
                                type="password" required
                                value={password} onChange={e => setPassword(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white text-sm focus:border-tennis-blue focus:outline-none"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    <button type="submit" className="w-full bg-tennis-blue hover:bg-blue-600 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2">
                        Sign In <ArrowRight className="w-4 h-4" />
                    </button>
                </form>

                <div className="relative my-6">
                    <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-800"></div></div>
                    <div className="relative flex justify-center text-xs uppercase"><span className="bg-slate-900 px-2 text-slate-500">Or continue with</span></div>
                </div>

                <div className="flex justify-center">
                    <GoogleLogin
                        onSuccess={async (cred) => {
                            const success = await googleLogin(cred);
                            if (success) navigate('/');
                        }}
                        onError={() => setError('Google Login Failed')}
                        theme="filled_black"
                        shape="circle"
                    />
                </div>

                <p className="mt-8 text-center text-xs text-slate-500">
                    Don't have an account? <Link to="/signup" className="text-tennis-blue hover:underline">Sign up</Link>
                </p>
            </div>
        </div>
    );
};

export const SignupPage = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const res = await axios.post('/api/auth/register', { email, password, full_name: name });
            login(res.data.access_token, res.data.user);
            setSuccess(true);
            setTimeout(() => navigate('/'), 2000);
        } catch (err) {
            setError(err.response?.data?.detail || 'Signup failed');
        }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-tennis-dark flex items-center justify-center p-4">
                <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-12 text-center animate-in fade-in zoom-in-95">
                    <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Check className="w-8 h-8 text-emerald-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Account Created!</h2>
                    <p className="text-slate-400">Welcome to CourtSide. Redirecting you...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-tennis-dark flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-8 shadow-2xl animate-in fade-in zoom-in-95 duration-300">
                <h1 className="text-2xl font-bold text-white mb-2 text-center">Create Account</h1>
                <p className="text-slate-400 text-sm text-center mb-8">Join the ultimate tennis analytics platform</p>

                {error && <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs p-3 rounded-lg mb-4 text-center">{error}</div>}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-500 uppercase">Full Name</label>
                        <div className="relative">
                            <User className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                            <input
                                type="text" required
                                value={name} onChange={e => setName(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white text-sm focus:border-tennis-blue focus:outline-none"
                                placeholder="John Doe"
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-500 uppercase">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                            <input
                                type="email" required
                                value={email} onChange={e => setEmail(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white text-sm focus:border-tennis-blue focus:outline-none"
                                placeholder="name@example.com"
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-500 uppercase">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                            <input
                                type="password" required
                                value={password} onChange={e => setPassword(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white text-sm focus:border-tennis-blue focus:outline-none"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    <button type="submit" className="w-full bg-tennis-blue hover:bg-blue-600 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2">
                        Create Account <ArrowRight className="w-4 h-4" />
                    </button>
                </form>

                <p className="mt-8 text-center text-xs text-slate-500">
                    Already have an account? <Link to="/login" className="text-tennis-blue hover:underline">Sign in</Link>
                </p>
            </div>
        </div>
    );
};
