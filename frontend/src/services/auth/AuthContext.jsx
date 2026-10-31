import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('sms_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('sms_access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then((profile) => {
        setUser(profile);
        localStorage.setItem('sms_user', JSON.stringify(profile));
      })
      .catch(() => {
        localStorage.removeItem('sms_access_token');
        localStorage.removeItem('sms_refresh_token');
        localStorage.removeItem('sms_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const saveSession = (authResponse) => {
    localStorage.setItem('sms_access_token', authResponse.access_token);
    localStorage.setItem('sms_refresh_token', authResponse.refresh_token);
    localStorage.setItem('sms_user', JSON.stringify(authResponse.user));
    setUser(authResponse.user);
    return authResponse.user;
  };

  const login = async (email, password) => {
    const res = await authApi.login({ email, password });
    return saveSession(res);
  };

  const register = async (payload) => {
    const res = await authApi.register(payload);
    return saveSession(res);
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore network errors on logout cleanup
    } finally {
      localStorage.removeItem('sms_access_token');
      localStorage.removeItem('sms_refresh_token');
      localStorage.removeItem('sms_user');
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAdmin: user?.role === 'admin',
    isStaff: user?.role === 'staff' || user?.role === 'admin',
    isCustomer: user?.role === 'customer',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
};

