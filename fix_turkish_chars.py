#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Turkish character encoding issues in TranscriptionDetailPage.tsx
"""

import os
import re

WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")
BACKUP_PATH = FILE_PATH + ".turkish_backup"

# Turkish character mappings
TURKISH_FIXES = [
    # Common corrupted patterns
    ('Se�imi', 'Seçimi'),
    ('�zel', 'Özel'),
    ('�eviri', 'Çeviri'),
    ('�rn:', 'Örn:'),
    ('Iyilestirme', 'İyileştirme'),
    ('Sinav', 'Sınav'),
    ('Notlari', 'Notları'),
    ('Sorulari', 'Soruları'),
    ('olusturuldu', 'oluşturuldu'),
    ('olusturulamadi', 'oluşturulamadı'),
    ('basariyla', 'başarıyla'),
    ('islemi', 'işlemi'),
    ('istediginiz', 'istediğiniz'),
    ('�', 'ç'),  # Generic fallback
    
    # Alert messages - full replacements
    ("'? Ders notlari basariyla olusturuldu!'", "'✅ Ders notları başarıyla oluşturuldu!'"),
    ("'? Lecture notes generated successfully!'", "'✅ Lecture notes generated successfully!'"),
    ("'? Ders notlari olusturulamadi: '", "'❌ Ders notları oluşturulamadı: '"),
    ("'? Failed to generate lecture notes: '", "'❌ Failed to generate lecture notes: '"),
    
    # Placeholder text
    ('placeholder="AI\'dan istediginiz �zel islemi buraya yazin... (�rn:', 
     'placeholder="AI\'dan istediğiniz özel işlemi buraya yazın... (Örn:'),
    
    # Operation labels in credit transactions
    ("{ tr: 'AI Iyilestirme'", "{ tr: 'AI İyileştirme'"),
    ("{ tr: 'Ders Notlari'", "{ tr: 'Ders Notları'"),
    ("{ tr: 'Sinav Sorulari'", "{ tr: 'Sınav Soruları'"),
    ("{ tr: '�zel Prompt'", "{ tr: 'Özel Prompt'"),
    ("{ tr: '�eviri'", "{ tr: 'Çeviri'"),
]

def fix_turkish_encoding():
    """Fix Turkish character encoding issues"""
    
    # Create backup
    if not os.path.exists(BACKUP_PATH):
        print(f"📦 Creating backup: {BACKUP_PATH}")
        with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Backup created")
    else:
        print("ℹ️ Using existing backup")
        with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    
    print(f"\n📖 Reading file: {FILE_PATH}")
    
    # Count initial issues
    initial_issues = sum(content.count(old) for old, new in TURKISH_FIXES)
    print(f"🔍 Found {initial_issues} Turkish encoding issues")
    
    # Apply fixes
    replacements_made = 0
    for old, new in TURKISH_FIXES:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements_made += count
            print(f"  ✓ Fixed {count}x: {old[:40]}... → {new[:40]}...")
    
    # Count remaining issues
    remaining_issues = sum(content.count(old) for old, new in TURKISH_FIXES)
    
    # Write back with UTF-8 encoding
    print(f"\n💾 Writing changes with UTF-8 encoding...")
    with open(FILE_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ TURKISH CHARACTER FIX COMPLETED!")
    print(f"{'='*60}")
    print(f"📊 Initial issues: {initial_issues}")
    print(f"🔧 Replacements made: {replacements_made}")
    print(f"⚠️ Remaining issues: {remaining_issues}")
    print(f"📁 Backup: {BACKUP_PATH}")
    
    if remaining_issues == 0:
        print("\n🎉 All Turkish characters fixed!")
    else:
        print(f"\n⚠️ {remaining_issues} issues may still remain")

if __name__ == "__main__":
    fix_turkish_encoding()
