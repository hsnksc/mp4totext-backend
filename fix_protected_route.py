#!/usr/bin/env python3
"""
ProtectedRoute.tsx düzeltmesi
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

PROTECTED_ROUTE = """import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  console.log('ProtectedRoute - User:', user, 'Loading:', loading);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    console.log('ProtectedRoute - No user, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  console.log('ProtectedRoute - User authenticated, rendering children');
  return <>{children}</>;
};
"""

print("🔧 ProtectedRoute.tsx düzeltiliyor...\n")

route_path = os.path.join(WEB_SRC, "components", "ProtectedRoute.tsx")
os.makedirs(os.path.dirname(route_path), exist_ok=True)
with open(route_path, "w", encoding="utf-8") as f:
    f.write(PROTECTED_ROUTE)

print("✅ components/ProtectedRoute.tsx düzeltildi!")
print("\n📍 Değişiklikler:")
print("   • Console.log ile debug mesajları eklendi")
print("   • Loading state kontrolü eklendi")
print("   • Replace flag eklendi Navigate'e")
