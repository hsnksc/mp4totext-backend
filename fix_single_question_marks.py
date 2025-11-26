#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix remaining single ? marks with proper emojis
"""

import os

WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")

# Single ? mark replacements
SINGLE_QUESTION_FIXES = [
    # Console logs
    ("console.log('? Default model set:", "console.log('🎯 Default model set:"),
    ("console.log('? Pricing and models loaded successfully')", "console.log('✅ Pricing and models loaded successfully')"),
    ("console.error('? Failed to fetch pricing or models:", "console.error('❌ Failed to fetch pricing or models:"),
    ("console.log('? Enhanced Text:", "console.log('✨ Enhanced Text:"),
    ("console.error('? Failed to fetch credit transactions:", "console.error('❌ Failed to fetch credit transactions:"),
    
    # Alert messages - Success
    ("alert('? Custom prompt applied successfully!')", "alert('✅ Custom prompt applied successfully!')"),
    ("alert('? Translation completed successfully!')", "alert('✅ Translation completed successfully!')"),
    ("'? Ders notlari başarıyla oluşturuldu!'", "'✅ Ders notları başarıyla oluşturuldu!'"),
    
    # Alert messages - Error
    ("alert('? Failed to apply custom prompt:", "alert('❌ Failed to apply custom prompt:"),
    ("alert('? Failed to generate exam questions:", "alert('❌ Failed to generate exam questions:"),
    ("alert('? Failed to translate:", "alert('❌ Failed to translate:"),
    ("'? Ders notlari oluşturulamadı:", "'❌ Ders notları oluşturulamadı:"),
    
    # Download all text sections
    ("allText += '? AI CLEANED TEXT", "allText += '🧹 AI CLEANED TEXT"),
    ("allText += `? AI ENHANCED TEXT", "allText += `✨ AI ENHANCED TEXT"),
    
    # UI labels
    ('<div className="text-xs text-blue-600 mb-1">? Processing Time</div>', 
     '<div className="text-xs text-blue-600 mb-1">⏱️ Processing Time</div>'),
    ('<div className="font-semibold mb-1">? Error</div>',
     '<div className="font-semibold mb-1">⚠️ Error</div>'),
    ('? Fillers removed, errors fixed by Together AI',
     '🧹 Fillers removed, errors fixed by Together AI'),
    ('<>? AI Cleaned Text (Together AI - Fallback)</>',
     '<>🧹 AI Cleaned Text (Together AI - Fallback)</>'),
    ('<>? AI Enhanced Text (',
     '<>✨ AI Enhanced Text ('),
    ('<span className="text-xs font-semibold text-pink-700">? Length:</span>',
     '<span className="text-xs font-semibold text-pink-700">📏 Length:</span>'),
    ('<span className="ml-2 text-green-600">? Correct</span>',
     '<span className="ml-2 text-green-600">✅ Correct</span>'),
    
    # Button labels
    ('<span>? Apply Prompt</span>',
     '<span>▶️ Apply Prompt</span>'),
    ('? Generate',
     '▶️ Generate'),
]

def fix_single_question_marks():
    """Fix single ? marks with proper emojis"""
    
    print("📖 Reading file...")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Count issues
    initial_count = sum(content.count(old) for old, new in SINGLE_QUESTION_FIXES)
    print(f"🔍 Found {initial_count} single ? marks to fix")
    
    # Apply fixes
    replacements = 0
    for old, new in SINGLE_QUESTION_FIXES:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements += count
            print(f"  ✓ Fixed {count}x: {old[:50]}... → {new[:50]}...")
    
    # Write back
    print(f"\n💾 Writing changes...")
    with open(FILE_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print(f"\n{'='*60}")
    print(f"✅ SINGLE ? MARKS FIXED!")
    print(f"{'='*60}")
    print(f"📊 Initial ? marks: {initial_count}")
    print(f"🔧 Fixed: {replacements}")
    
    if replacements > 0:
        print("🎉 All single ? marks replaced with meaningful emojis!")

if __name__ == "__main__":
    fix_single_question_marks()
