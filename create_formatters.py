"""
Create missing formatters utility
"""

from pathlib import Path

FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")
FORMATTERS = FRONTEND_PATH / "src" / "utils" / "formatters.ts"

FORMATTERS_CONTENT = '''/**
 * Format seconds to MM:SS or HH:MM:SS
 */
export function formatDuration(seconds: number | null): string {
  if (!seconds) return '00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format bytes to human-readable size
 */
export function formatFileSize(bytes: number | null): string {
  if (!bytes) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

/**
 * Format ISO date string to localized date and time
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return '-';
  
  const date = new Date(dateString);
  
  return new Intl.DateTimeFormat('tr-TR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return '-';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffSecs < 60) return 'Az önce';
  if (diffMins < 60) return `${diffMins} dakika önce`;
  if (diffHours < 24) return `${diffHours} saat önce`;
  if (diffDays < 7) return `${diffDays} gün önce`;
  
  return formatDate(dateString);
}

/**
 * Format processing time in seconds to human-readable format
 */
export function formatProcessingTime(seconds: number | null): string {
  if (!seconds) return '-';
  
  if (seconds < 60) {
    return `${Math.floor(seconds)} saniye`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSecs = Math.floor(seconds % 60);
  
  if (minutes < 60) {
    return remainingSecs > 0 
      ? `${minutes} dakika ${remainingSecs} saniye`
      : `${minutes} dakika`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMins = minutes % 60;
  
  return remainingMins > 0
    ? `${hours} saat ${remainingMins} dakika`
    : `${hours} saat`;
}
'''

def main():
    print("\n📝 Creating formatters utility...")
    print("=" * 50)
    
    try:
        FORMATTERS.parent.mkdir(parents=True, exist_ok=True)
        print(f"📝 Writing {FORMATTERS.name}...")
        FORMATTERS.write_text(FORMATTERS_CONTENT, encoding='utf-8')
        print(f"✅ {FORMATTERS.name} created successfully!")
        print("\n📋 Available functions:")
        print("   • formatDuration(seconds)")
        print("   • formatFileSize(bytes)")
        print("   • formatDate(dateString)")
        print("   • formatRelativeTime(dateString)")
        print("   • formatProcessingTime(seconds)")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()
