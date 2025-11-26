#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix remaining Turkish character issues - Phase 2
"""

import os

WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")

# Additional Turkish character fixes
TURKISH_FIXES_PHASE2 = [
    # Placeholder text
    ('yazin...', 'yazın...'),
    ('formatina', 'formatına'),
    ('basliklar', 'başlıklar'),
    
    # Other common words
    ('aciklarken', 'açıklarken'),
    ('aciklama', 'açıklama'),
    ('degistir', 'değiştir'),
    ('duzenle', 'düzenle'),
    ('guncel', 'güncel'),
    ('goruntule', 'görüntüle'),
    ('indir', 'indir'),
    ('kaydet', 'kaydet'),
    ('kopyala', 'kopyala'),
    ('yuksek', 'yüksek'),
    ('dusuk', 'düşük'),
]

def fix_turkish_phase2():
    """Fix remaining Turkish character issues"""
    
    print("📖 Reading file...")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Count issues
    initial_count = sum(content.count(old) for old, new in TURKISH_FIXES_PHASE2)
    print(f"🔍 Found {initial_count} remaining issues")
    
    # Apply fixes
    replacements = 0
    for old, new in TURKISH_FIXES_PHASE2:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements += count
            print(f"  ✓ Fixed {count}x: {old} → {new}")
    
    # Write back
    print(f"\n💾 Writing changes...")
    with open(FILE_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print(f"\n{'='*60}")
    print(f"✅ PHASE 2 COMPLETED!")
    print(f"{'='*60}")
    print(f"🔧 Fixed {replacements} remaining Turkish character issues")
    
    if replacements > 0:
        print("🎉 All Turkish characters now properly encoded!")

if __name__ == "__main__":
    fix_turkish_phase2()
