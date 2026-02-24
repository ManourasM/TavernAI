import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import './LoginPage.css';

export default function LoginPage() {
  const { login, signup, isLoading, error: storeError, needsBootstrap, checkBootstrap, initializeAuth, isAuthenticated } = useAuthStore();
  const navigate = useNavigate();
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [localError, setLocalError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Initialize auth and check bootstrap on mount
  useEffect(() => {
    initializeAuth();
    checkBootstrap();
  }, [initializeAuth, checkBootstrap]);

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    setSuccessMessage('');

    // Validate inputs
    if (!username.trim()) {
      setLocalError('Username is required');
      return;
    }
    if (!password) {
      setLocalError('Password is required');
      return;
    }

    try {
      if (isSignup) {
        // Handle signup
        const result = await signup(username, password);
        if (result.success) {
          setSuccessMessage('Account created! Please log in with your credentials.');
          setIsSignup(false);
          setPassword('');
          // Don't navigate away - user needs to login
        } else {
          setLocalError(result.error || 'Signup failed');
        }
      } else {
        // Handle login
        const result = await login(username, password);
        if (result.success) {
          setSuccessMessage('Logged in successfully! Redirecting...');
          // Navigation will happen automatically via useEffect watching isAuthenticated
        } else {
          setLocalError(result.error || 'Login failed');
        }
      }
    } catch (err) {
      setLocalError(err.message || 'An error occurred');
    }
  };

  // Toggle between login and signup
  const handleToggleMode = () => {
    setIsSignup(!isSignup);
    setLocalError('');
    setSuccessMessage('');
    setPassword('');
  };

  const displayError = localError || storeError;

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          {/* Header */}
          <div className="login-header">
            <h1>🍽️ TavernAI</h1>
            <p className="subtitle">
              {isSignup ? 'Create Admin Account' : 'Sign In'}
            </p>
          </div>

          {/* Error Message */}
          {displayError && (
            <div className="alert alert-error" role="alert">
              <span className="alert-icon">⚠️</span>
              <span className="alert-text">{displayError}</span>
            </div>
          )}

          {/* Success Message */}
          {successMessage && (
            <div className="alert alert-success" role="alert">
              <span className="alert-icon">✓</span>
              <span className="alert-text">{successMessage}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="login-form">
            {/* Username Input */}
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                className="form-input"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
                autoFocus
                autoComplete="username"
              />
            </div>

            {/* Password Input */}
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                autoComplete={isSignup ? 'new-password' : 'current-password'}
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner"></span>
                  {isSignup ? 'Creating...' : 'Signing in...'}
                </>
              ) : (
                isSignup ? 'Create Account' : 'Sign In'
              )}
            </button>
          </form>

          {/* Toggle Login / Signup */}
          <div className="login-footer">
            {needsBootstrap && (
              <>
                {isSignup ? (
                  <p>
                    Already have an account?{' '}
                    <button
                      type="button"
                      className="link-button"
                      onClick={handleToggleMode}
                      disabled={isLoading}
                    >
                      Sign in instead
                    </button>
                  </p>
                ) : (
                  <p>
                    No account yet?{' '}
                    <button
                      type="button"
                      className="link-button"
                      onClick={handleToggleMode}
                      disabled={isLoading}
                    >
                      Create admin account
                    </button>
                  </p>
                )}
              </>
            )}
          </div>

          {/* Help Text */}
          <div className="login-help">
            <p className="help-text">
              {needsBootstrap
                ? 'Create an admin account to get started'
                : 'Sign in with your credentials'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

