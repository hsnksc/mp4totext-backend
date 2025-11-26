#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix remaining emoji placeholders - Phase 2
Focus on language flags and other remaining issues
"""

import os

WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")

# Additional replacements for Phase 2
PHASE2_REPLACEMENTS = [
    # Language flags in select dropdown (4 question marks each)
    ('<option value="en">???? English</option>', '<option value="en">🇬🇧 English</option>'),
    ('<option value="tr">???? Turkish</option>', '<option value="tr">🇹🇷 Turkish</option>'),
    ('<option value="de">???? German</option>', '<option value="de">🇩🇪 German</option>'),
    ('<option value="fr">???? French</option>', '<option value="fr">🇫🇷 French</option>'),
    ('<option value="es">???? Spanish</option>', '<option value="es">🇪🇸 Spanish</option>'),
    ('<option value="it">???? Italian</option>', '<option value="it">🇮🇹 Italian</option>'),
    ('<option value="pt">???? Portuguese</option>', '<option value="pt">🇵🇹 Portuguese</option>'),
    ('<option value="ru">???? Russian</option>', '<option value="ru">🇷🇺 Russian</option>'),
    ('<option value="ar">???? Arabic</option>', '<option value="ar">🇸🇦 Arabic</option>'),
    ('<option value="zh">???? Chinese</option>', '<option value="zh">🇨🇳 Chinese</option>'),
    ('<option value="ja">???? Japanese</option>', '<option value="ja">🇯🇵 Japanese</option>'),
    ('<option value="ko">???? Korean</option>', '<option value="ko">🇰🇷 Korean</option>'),
    
    # Language names object (Cyrillic, Arabic, Chinese, Japanese, Korean)
    ("ru: '???????',", "ru: 'Русский',"),
    ("ar: '???????',", "ar: 'العربية',"),
    ("zh: '??',", "zh: '中文',"),
    ("ja: '???',", "ja: '日本語',"),
    ("ko: '???'", "ko: '한국어'"),
    
    # Translation header
    ('?? {languageNames[langCode]', '🌐 {languageNames[langCode]'),
    
    # Console logs
    ("console.log('?? Summary:", "console.log('📝 Summary:"),
    ("console.log('?? Models count:", "console.log('📊 Models count:"),
    
    # Nullish coalescing operator (not an emoji!)
    # This should NOT be replaced: (transcription.speaker_count ?? 0)
    # We'll skip this one
    
    # Custom prompt & translation
    ("custom_prompt: { tr: 'Özel Prompt', en: 'Custom Prompt', icon: '??' }", 
     "custom_prompt: { tr: 'Özel Prompt', en: 'Custom Prompt', icon: '💬' }"),
    ("translation: { tr: 'Çeviri', en: 'Translation', icon: '??' }",
     "translation: { tr: 'Çeviri', en: 'Translation', icon: '🌐' }"),
    
    # Fallback operation
    ("operationLabels[tx.operation_type] || { tr: tx.operation_type, en: tx.operation_type, icon: '??' }",
     "operationLabels[tx.operation_type] || { tr: tx.operation_type, en: tx.operation_type, icon: '📌' }"),
]

def fix_phase2():
    """Apply Phase 2 replacements"""
    
    print("📖 Reading file...")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    initial_count = content.count('??')
    print(f"🔍 Initial '??' count: {initial_count}")
    
    replacements_made = 0
    for old, new in PHASE2_REPLACEMENTS:
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
    print(f"✅ PHASE 2 COMPLETED!")
    print(f"{'='*60}")
    print(f"📊 Initial '??' count: {initial_count}")
    print(f"🔧 Replacements made: {replacements_made}")
    print(f"⚠️ Remaining '??' count: {remaining_count}")
    
    if remaining_count > 0:
        print(f"\n⚠️ Note: {remaining_count} instances remain")
        print("Some may be legitimate code (e.g., ?? nullish coalescing operator)")
    else:
        print("\n🎉 All emoji placeholders fixed!")

if __name__ == "__main__":
    fix_phase2()
