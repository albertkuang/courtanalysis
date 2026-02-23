import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Mail, Lock, User, Chrome } from 'lucide-react';

const LoginModal = ({ onClose, onLogin }) => {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Google Sign-In (Real) - Disabled until a valid Client ID is provided
  // useEffect(() => {
  //   /* global google */
  //   if (window.google) {
  //     google.accounts.id.initialize({
  //       client_id: "YOUR_GOOGLE_CLIENT_ID", // TODO: Replace with env var
  //       callback: handleGoogleCallback
  //     });
  //     google.accounts.id.renderButton(
  //       document.getElementById("googleSignInDiv"),
  //       { theme: "outline", size: "large", width: "100%" }
  //     );
  //   } else {
  //     // Dynamically load script if missing
  //     const script = document.createElement('script');
  //     script.src = "https://accounts.google.com/gsi/client";
  //     script.async = true;
  //     script.defer = true;
  //     script.onload = () => {
  //       if (window.google) {
  //         window.google.accounts.id.initialize({
  //           client_id: "YOUR_GOOGLE_CLIENT_ID",
  //           callback: handleGoogleCallback
  //         });
  //         window.google.accounts.id.renderButton(
  //           document.getElementById("googleSignInDiv"),
  //           { theme: "outline", size: "large", width: "100%" }
  //         );
  //       }
  //     };
  //     document.body.appendChild(script);
  //   }
  // }, []);

  const handleGoogleCallback = async (response) => {
    setLoading(true);
    setError('');
    try {
      const res = await axios.post('/api/auth/google', { token: response.credential });
      onLogin(res.data);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Google Login Failed');
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      let res;
      if (isSignup) {
        // Register (Using /api/auth/register and JSON)
        res = await axios.post('/api/auth/register', { email, password, full_name: name });
      } else {
        // Login (Using /api/auth/login and Form Data for OAuth2 spec)
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        res = await axios.post('/api/auth/login', formData);
      }

      onLogin(res.data);
      onClose();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Authentication failed');
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden relative animate-in zoom-in-95 duration-200">

        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">
              {isSignup ? 'Create Account' : 'Welcome Back'}
            </h2>
            <p className="text-slate-400 text-sm">
              {isSignup ? 'Sign up to unlock advanced features' : 'Sign in to your account'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignup && (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase">Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-tennis-blue"
                    placeholder="John Doe"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-tennis-blue"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-tennis-blue"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {error && <div className="text-rose-500 text-sm">{error}</div>}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-tennis-blue hover:bg-blue-600 text-white font-semibold py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? 'Processing...' : (isSignup ? 'Sign Up' : 'Sign In')}
            </button>
          </form>

          <div className="my-6 flex items-center gap-4">
            <div className="h-px bg-slate-800 flex-1"></div>
            <span className="text-xs text-slate-500">OR</span>
            <div className="h-px bg-slate-800 flex-1"></div>
          </div>

          <div id="googleSignInDiv" className="w-full flex justify-center"></div>

          <button
            onClick={() => handleGoogleCallback({ credential: "MOCK_TOKEN" })}
            className="w-full mt-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 py-2 rounded-lg flex items-center justify-center gap-2 text-sm transition-colors"
          >
            <Chrome className="w-4 h-4" /> (Dev Helper) Mock Google Login
          </button>

          <div className="mt-6 text-center text-sm text-slate-400">
            {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => setIsSignup(!isSignup)}
              className="text-tennis-blue hover:underline font-medium"
            >
              {isSignup ? 'Sign In' : 'Sign Up'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;
