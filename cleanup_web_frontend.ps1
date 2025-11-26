# Web Frontend Cleanup Script - Remove old speaker recognition system
$webPath = 'c:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web'

Write-Host ' Web Frontend Temizliği Başlıyor...' -ForegroundColor Cyan

# 1. UploadPage.tsx - Eski state'leri kaldır, pyannote state'leri ekle
Write-Host '   UploadPage.tsx state güncellemesi...' -ForegroundColor Yellow
$uploadPage = Get-Content "$webPath\src\pages\UploadPage.tsx" -Raw

# State tanımlarını güncelle
$uploadPage = $uploadPage -replace '  // Removed: useSpeakerRecognition \(old system\)\r?\n  // Removed: speakerModelType \(old system\)', @'
  // NEW: pyannote.audio 3.1 Modal diarization states
  const [enableDiarization, setEnableDiarization] = useState(false);
  const [minSpeakers, setMinSpeakers] = useState<string>('');
  const [maxSpeakers, setMaxSpeakers] = useState<string>('');
'@

Set-Content "$webPath\src\pages\UploadPage.tsx" $uploadPage -NoNewline
Write-Host '   State'ler güncellendi' -ForegroundColor Green

Write-Host ' Temizlik tamamlandı!' -ForegroundColor Green
