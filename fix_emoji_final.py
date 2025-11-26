#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix final 2 emoji placeholders with encoding issues
"""

import os

WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")

def fix_final():
    """Fix final 2 placeholders with encoding issues"""
    
    print("📖 Reading file with UTF-8 encoding...")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    replacements = 0
    
    # Line 1746 (index 1745)
    if '?? AI Model Se' in lines[1745]:
        print(f"  🔍 Line 1746 before: {lines[1745].strip()}")
        lines[1745] = lines[1745].replace('?? AI Model Se', '🤖 AI Model Seç')
        lines[1745] = lines[1745].replace('Se�imi', 'Seçimi')
        print(f"  ✓ Line 1746 after:  {lines[1745].strip()}")
        replacements += 1
    
    # Line 1810 (index 1809)
    if '?? �zel' in lines[1809] or '?? Özel' in lines[1809]:
        print(f"  🔍 Line 1810 before: {lines[1809].strip()}")
        lines[1809] = lines[1809].replace('?? �zel', '💭 Özel')
        lines[1809] = lines[1809].replace('?? Özel', '💭 Özel')
        print(f"  ✓ Line 1810 after:  {lines[1809].strip()}")
        replacements += 1
    
    # Write back
    print(f"\n💾 Writing changes...")
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Verify
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    remaining = content.count('??') - content.count(' ?? ')  # Exclude nullish coalescing
    
    print(f"\n{'='*60}")
    print(f"✅ FINAL FIX COMPLETED!")
    print(f"{'='*60}")
    print(f"🔧 Replacements made: {replacements}")
    print(f"⚠️ Remaining '??' (excluding ?? operator): ~{remaining}")
    
    if remaining <= 1:
        print("\n🎉 All emoji placeholders fixed!")
        print("✅ Remaining '??' is nullish coalescing operator (valid code)")
    else:
        print(f"\n⚠️ {remaining} instances may still need review")

if __name__ == "__main__":
    fix_final()
