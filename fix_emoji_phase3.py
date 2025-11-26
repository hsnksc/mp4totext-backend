#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix final emoji placeholders - Phase 3
"""

import os

WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")

PHASE3_REPLACEMENTS = [
    # Topic label
    ('?? {q.topic}', '🏷️ {q.topic}'),
    
    # Summary section (second occurrence)
    ('<h3 className="text-xl font-bold text-gray-800">?? Summary</h3>', 
     '<h3 className="text-xl font-bold text-gray-800">📝 Summary</h3>'),
    
    # AI Model selection (Turkish text)
    ('?? AI Model Seçimi (Her Modelin Kredi Maliyeti)', 
     '🤖 AI Model Seçimi (Her Modelin Kredi Maliyeti)'),
    
    # Custom Prompt Text (Turkish) - second occurrence
    ('?? Özel Prompt Metni', '💭 Özel Prompt Metni'),
]

def fix_phase3():
    """Apply Phase 3 final replacements"""
    
    print("📖 Reading file...")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    initial_count = content.count('??')
    print(f"🔍 Initial '??' count: {initial_count}")
    
    replacements_made = 0
    for old, new in PHASE3_REPLACEMENTS:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements_made += count
            print(f"  ✓ Replaced {count}x: {old[:50]}...")
    
    remaining_count = content.count('??')
    
    print(f"\n💾 Writing changes...")
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n{'='*60}")
    print(f"✅ PHASE 3 COMPLETED!")
    print(f"{'='*60}")
    print(f"📊 Initial '??' count: {initial_count}")
    print(f"🔧 Replacements made: {replacements_made}")
    print(f"⚠️ Remaining '??' count: {remaining_count}")
    
    if remaining_count == 1:
        print(f"\n✅ Only 1 '??' remains (likely nullish coalescing operator)")
        print("This is legitimate TypeScript syntax and should NOT be changed.")
    elif remaining_count > 1:
        print(f"\n⚠️ {remaining_count} instances remain - review needed")
    else:
        print("\n🎉 All emoji placeholders fixed!")

if __name__ == "__main__":
    fix_phase3()
