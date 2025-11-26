"""
Test Audio Upload Script
"""
import requests
from pathlib import Path

def upload_audio_file():
    """Test audio dosyasını API'ye yükle"""
    
    # Token'ı oku
    with open("test_token.txt", "r") as f:
        token = f.read().strip()
    
    # Audio dosyası
    audio_file = Path("test_files/test_audio.wav")
    
    if not audio_file.exists():
        print(f"❌ Audio dosyası bulunamadı: {audio_file}")
        return None
    
    print(f"\n📤 Audio dosyası yükleniyor...")
    print(f"   Dosya: {audio_file}")
    print(f"   Boyut: {audio_file.stat().st_size:,} bytes")
    
    # API request
    url = "http://localhost:8000/api/v1/transcriptions/upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Dosya ve form data
    with open(audio_file, 'rb') as f:
        files = {
            'file': ('test_audio.wav', f, 'audio/wav')
        }
        data = {
            'language': 'tr',
            'use_speaker_recognition': 'false'
        }
        
        try:
            response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            
            print(f"\n📊 Response Status: {response.status_code}")
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                print(f"✅ Upload başarılı!\n")
                print(f"📋 Transcription Details:")
                print(f"   ID: {result.get('id')}")
                print(f"   Status: {result.get('status')}")
                print(f"   File Name: {result.get('file_name')}")
                print(f"   File Size: {result.get('file_size'):,} bytes")
                print(f"   Language: {result.get('language')}")
                print(f"   Created: {result.get('created_at')}")
                
                # ID'yi kaydet
                transcription_id = result.get('id')
                with open("transcription_id.txt", "w") as f:
                    f.write(str(transcription_id))
                
                print(f"\n💾 Transcription ID kaydedildi: {transcription_id}")
                return transcription_id
            else:
                print(f"❌ Upload başarısız!")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request hatası: {e}")
            return None

if __name__ == "__main__":
    transcription_id = upload_audio_file()
    
    if transcription_id:
        print(f"\n✨ Başarılı! Transkripsiyon ID: {transcription_id}")
        print(f"\n💡 Durumu kontrol etmek için:")
        print(f"   python check_transcription.py {transcription_id}")
