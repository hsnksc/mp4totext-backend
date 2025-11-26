"""
Fix all import/export mismatches
"""

from pathlib import Path

FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")

# App.tsx - Fix imports to use default exports
APP_TSX = FRONTEND_PATH / "src" / "App.tsx"

FIXED_APP = '''import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import TranscriptionsPage from './pages/TranscriptionsPage';
import TranscriptionDetailPage from './pages/TranscriptionDetailPage';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/transcriptions" element={<TranscriptionsPage />} />
            <Route path="/transcriptions/:id" element={<TranscriptionDetailPage />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
'''

# FileUpload component
FILE_UPLOAD = FRONTEND_PATH / "src" / "components" / "FileUpload.tsx"

FILE_UPLOAD_CONTENT = '''import React, { useRef, useState } from 'react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  accept?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({ 
  onFileSelect, 
  disabled = false,
  accept = "audio/*,video/*"
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (disabled) return;
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
        transition-colors duration-200
        ${isDragging 
          ? 'border-blue-500 bg-blue-50' 
          : 'border-gray-300 hover:border-gray-400'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileInput}
        disabled={disabled}
        className="hidden"
      />
      
      <div className="flex flex-col items-center space-y-4">
        <svg
          className="w-16 h-16 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        
        <div>
          <p className="text-lg font-medium text-gray-700">
            {disabled ? 'Yükleniyor...' : 'Dosya seçin veya sürükleyin'}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            MP3, MP4, WAV, M4A, AVI, MOV, MKV
          </p>
        </div>
      </div>
    </div>
  );
};

export default FileUpload;
'''

def main():
    print("\n🔧 Fixing Import/Export Mismatches...")
    print("=" * 50)
    
    success_count = 0
    
    # Fix App.tsx
    try:
        print("📝 Fixing App.tsx imports...")
        APP_TSX.write_text(FIXED_APP, encoding='utf-8')
        print("✅ App.tsx fixed!")
        success_count += 1
    except Exception as e:
        print(f"❌ Failed to fix App.tsx: {e}")
    
    # Create FileUpload component
    try:
        FILE_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
        print("📝 Creating FileUpload.tsx...")
        FILE_UPLOAD.write_text(FILE_UPLOAD_CONTENT, encoding='utf-8')
        print("✅ FileUpload.tsx created!")
        success_count += 1
    except Exception as e:
        print(f"❌ Failed to create FileUpload.tsx: {e}")
    
    print("\n" + "=" * 50)
    if success_count == 2:
        print("✅ All import/export issues fixed!")
        print("\n📋 Changes:")
        print("   • App.tsx uses default imports")
        print("   • FileUpload.tsx created with default export")
        print("   • All components now use default exports")
    else:
        print(f"⚠️  {success_count}/2 fixes applied")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
