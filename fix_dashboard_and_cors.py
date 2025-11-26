#!/usr/bin/env python3
"""
1. DashboardPage - API response handling
2. Backend CORS - Upload endpoint
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"
BACKEND_API = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-backend\app\api\v1"

# Fix 1: DashboardPage - Handle API response properly
DASHBOARD_PAGE = """import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { transcriptionService } from '../services/transcriptionService';
import { Transcription } from '../types/transcription';
import { Layout } from '../components/Layout';

export const DashboardPage: React.FC = () => {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchTranscriptions();
  }, []);

  const fetchTranscriptions = async () => {
    try {
      setLoading(true);
      const data = await transcriptionService.getAll();
      console.log('API Response:', data);
      
      // Backend returns { transcriptions: [...] } or just [...]
      const transcriptionArray = Array.isArray(data) ? data : (data.transcriptions || []);
      
      setTranscriptions(transcriptionArray);
      setError('');
    } catch (err: any) {
      console.error('Failed to fetch transcriptions:', err);
      setError('Transkriptler yüklenirken hata oluştu');
      setTranscriptions([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return styles[status as keyof typeof styles] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Yükleniyor...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
        <p className="text-gray-600">Transkripsiyon işlemlerinizi yönetin</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Toplam</p>
              <p className="text-2xl font-bold text-gray-900">{transcriptions.length}</p>
            </div>
            <div className="bg-blue-100 rounded-full p-3">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Tamamlanan</p>
              <p className="text-2xl font-bold text-green-600">
                {transcriptions.filter(t => t.status === 'completed').length}
              </p>
            </div>
            <div className="bg-green-100 rounded-full p-3">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">İşleniyor</p>
              <p className="text-2xl font-bold text-blue-600">
                {transcriptions.filter(t => t.status === 'processing' || t.status === 'pending').length}
              </p>
            </div>
            <div className="bg-blue-100 rounded-full p-3">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Son Transkriptler</h2>
            <Link
              to="/upload"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              + Yeni Yükle
            </Link>
          </div>
        </div>

        <div className="p-6">
          {transcriptions.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">Henüz transkript yok</h3>
              <p className="mt-1 text-sm text-gray-500">İlk dosyanızı yükleyerek başlayın</p>
              <div className="mt-6">
                <Link
                  to="/upload"
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  Dosya Yükle
                </Link>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Dosya Adı
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Durum
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tarih
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      İşlem
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {transcriptions.map((transcription) => (
                    <tr key={transcription.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {transcription.filename}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(transcription.status)}`}>
                          {transcription.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(transcription.created_at).toLocaleDateString('tr-TR')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link
                          to={`/transcriptions/${transcription.id}`}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Görüntüle
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};
"""

# Fix 2: Backend CORS - Add trailing slash redirect handling
TRANSCRIPTIONS_API = """from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.transcription import Transcription
from app.api.dependencies import get_current_user
from app.tasks.transcription_task import process_transcription
import os
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=List[dict])
@router.get("", response_model=List[dict])  # Both with and without trailing slash
async def get_transcriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Get all transcriptions for current user\"\"\"
    transcriptions = db.query(Transcription).filter(
        Transcription.user_id == current_user.id
    ).order_by(Transcription.created_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "filename": t.filename,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "text": t.text,
            "enhanced_text": t.enhanced_text,
            "summary": t.summary,
            "language": t.language,
            "duration": t.duration,
            "file_size": t.file_size,
        }
        for t in transcriptions
    ]

@router.post("/upload", status_code=status.HTTP_201_CREATED)
@router.post("/upload/", status_code=status.HTTP_201_CREATED)  # Both with and without trailing slash
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Upload audio/video file for transcription\"\"\"
    
    # Validate file type
    allowed_types = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/m4a", "audio/x-m4a", "video/mp4"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 100MB)
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(status_code=400, detail="File too large. Max size: 100MB")
    
    # Save file
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create transcription record
    transcription = Transcription(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status="pending"
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # Start async task
    process_transcription.delay(transcription.id)
    
    return {
        "id": transcription.id,
        "filename": transcription.filename,
        "status": transcription.status,
        "message": "File uploaded successfully. Transcription started."
    }

@router.get("/{transcription_id}", response_model=dict)
async def get_transcription(
    transcription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Get specific transcription\"\"\"
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return {
        "id": transcription.id,
        "filename": transcription.filename,
        "status": transcription.status,
        "text": transcription.text,
        "enhanced_text": transcription.enhanced_text,
        "summary": transcription.summary,
        "language": transcription.language,
        "duration": transcription.duration,
        "file_size": transcription.file_size,
        "created_at": transcription.created_at.isoformat(),
        "updated_at": transcription.updated_at.isoformat(),
    }

@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Delete transcription\"\"\"
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Delete file
    if os.path.exists(transcription.file_path):
        os.remove(transcription.file_path)
    
    db.delete(transcription)
    db.commit()
    
    return None
"""

print("🔧 Dashboard ve CORS düzeltiliyor...\n")

# Update DashboardPage
dashboard_path = os.path.join(WEB_SRC, "pages", "DashboardPage.tsx")
with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(DASHBOARD_PAGE)
print("✅ DashboardPage.tsx düzeltildi!")

# Update Backend API
transcriptions_path = os.path.join(BACKEND_API, "transcriptions.py")
with open(transcriptions_path, "w", encoding="utf-8") as f:
    f.write(TRANSCRIPTIONS_API)
print("✅ transcriptions.py düzeltildi!")

print("\n📍 Değişiklikler:")
print("   • DashboardPage: API response array handling")
print("   • Backend: Trailing slash redirect fix")
print("   • Backend: Both / and '' endpoints added")
print("\n⚠️  Backend'i yeniden başlatın!")
