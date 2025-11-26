#!/usr/bin/env python3
"""
AuthContext.tsx düzeltmesi
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

AUTH_CONTEXT = """import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';
import type { User, LoginRequest, RegisterRequest } from '../types/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initAuth();
  }, []);

  const initAuth = async () => {
    try {
      const token = localStorage.getItem('token');
      if (token) {
        const userData = await authService.getProfile(token);
        setUser(userData);
      }
    } catch (error) {
      console.error('Auth initialization error:', error);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (data: LoginRequest) => {
    try {
      const response = await authService.login(data);
      localStorage.setItem('token', response.access_token);
      const userData = await authService.getProfile(response.access_token);
      setUser(userData);
    } catch (error) {
      throw error;
    }
  };

  const register = async (data: RegisterRequest) => {
    try {
      const response = await authService.register(data);
      localStorage.setItem('token', response.access_token);
      const userData = await authService.getProfile(response.access_token);
      setUser(userData);
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
"""

print("🔧 AuthContext.tsx düzeltiliyor...\n")

context_path = os.path.join(WEB_SRC, "contexts", "AuthContext.tsx")
os.makedirs(os.path.dirname(context_path), exist_ok=True)
with open(context_path, "w", encoding="utf-8") as f:
    f.write(AUTH_CONTEXT)

print("✅ contexts/AuthContext.tsx düzeltildi!")
print("\n📍 Değişiklikler:")
print("   • isAuthenticated çağrısı kaldırıldı")
print("   • Token kontrolü doğrudan yapılıyor")
print("   • Error handling iyileştirildi")
