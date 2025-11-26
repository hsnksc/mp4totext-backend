#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix emoji placeholders (??) in TranscriptionDetailPage.tsx
Replace with proper emojis based on context
"""

import os
import re

# File path
WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")
BACKUP_PATH = FILE_PATH + ".emoji_backup"

# Emoji mapping based on context
EMOJI_REPLACEMENTS = [
    # Headers and titles
    (r"<span className=\"text-4xl\">??</span>", '<span className="text-4xl">📄</span>'),  # Document icon
    
    # Language flags in translation
    (r"<option value=\"en\">???? English</option>", '<option value="en">🇬🇧 English</option>'),
    (r"<option value=\"tr\">???? Turkish</option>", '<option value="tr">🇹🇷 Turkish</option>'),
    (r"<option value=\"de\">???? German</option>", '<option value="de">🇩🇪 German</option>'),
    (r"<option value=\"fr\">???? French</option>", '<option value="fr">🇫🇷 French</option>'),
    (r"<option value=\"es\">???? Spanish</option>", '<option value="es">🇪🇸 Spanish</option>'),
    (r"<option value=\"it\">???? Italian</option>", '<option value="it">🇮🇹 Italian</option>'),
    (r"<option value=\"pt\">???? Portuguese</option>", '<option value="pt">🇵🇹 Portuguese</option>'),
    (r"<option value=\"ru\">???? Russian</option>", '<option value="ru">🇷🇺 Russian</option>'),
    (r"<option value=\"ar\">???? Arabic</option>", '<option value="ar">🇸🇦 Arabic</option>'),
    (r"<option value=\"zh\">???? Chinese</option>", '<option value="zh">🇨🇳 Chinese</option>'),
    (r"<option value=\"ja\">???? Japanese</option>", '<option value="ja">🇯🇵 Japanese</option>'),
    (r"<option value=\"ko\">???? Korean</option>", '<option value="ko">🇰🇷 Korean</option>'),
    
    # Language names in translation result
    (r"ru: '\?\?\?\?\?\?\?'", "ru: 'Русский'"),
    (r"ar: '\?\?\?\?\?\?\?'", "ar: 'العربية'"),
    (r"zh: '\?\?'", "zh: '中文'"),
    (r"ja: '\?\?\?'", "ja: '日本語'"),
    (r"ko: '\?\?\?'", "ko: '한국어'"),
    
    # AI Provider logos
    (r'<div className="text-xl">??</div>\s*<div className="text-sm font-semibold">Gemini</div>', '<div className="text-xl">✨</div>\n                    <div className="text-sm font-semibold">Gemini</div>'),
    (r'<div className="text-xl">??</div>\s*<div className="text-sm font-semibold">OpenAI</div>', '<div className="text-xl">🤖</div>\n                    <div className="text-sm font-semibold">OpenAI</div>'),
    (r'<div className="text-xl">??</div>\s*<div className="text-sm font-semibold">Together AI</div>', '<div className="text-xl">🚀</div>\n                    <div className="text-sm font-semibold">Together AI</div>'),
    
    # Large AI provider icons in modal
    (r'<div className="text-2xl mb-2">??</div>\s*<div className="font-semibold text-gray-800">Gemini</div>', '<div className="text-2xl mb-2">✨</div>\n                    <div className="font-semibold text-gray-800">Gemini</div>'),
    (r'<div className="text-2xl mb-2">??</div>\s*<div className="font-semibold text-gray-800">OpenAI</div>', '<div className="text-2xl mb-2">🤖</div>\n                    <div className="font-semibold text-gray-800">OpenAI</div>'),
    (r'<div className="text-2xl mb-2">??</div>\s*<div className="font-semibold text-gray-800">Together AI</div>', '<div className="text-2xl mb-2">🚀</div>\n                    <div className="font-semibold text-gray-800">Together AI</div>'),
    
    # Provider badges
    (r"provider === 'groq' && '\? Groq'", "provider === 'groq' && '⚡ Groq'"),
    (r"provider === 'openai' && '\?\? OpenAI'", "provider === 'openai' && '🤖 OpenAI'"),
    (r"provider === 'gemini' && '\? Gemini'", "provider === 'gemini' && '✨ Gemini'"),
    
    # Section headers
    (r'?? Component mounted', '🔧 Component mounted'),
    (r'\?\? Making API call', '📡 Making API call'),
    (r'\?\? Pricing response', '💰 Pricing response'),
    (r'\?\? AI Models response', '🤖 AI Models response'),
    (r'\?\? Models count', '📊 Models count'),
    (r'\?\? Polling', '🔄 Polling'),
    (r'\?\? API Response', '📥 API Response'),
    (r'\?\? Full Response Keys', '🔑 Full Response Keys'),
    (r'\?\? Summary', '📝 Summary'),
    (r'\?\? Gemini Status', '⚡ Gemini Status'),
    (r'\?\? use_gemini', '🔧 use_gemini'),
    (r'\?\? Loaded .* credit transactions', '💳 Loaded credit transactions'),
    (r'\?\? Please enter a custom prompt', '⚠️ Please enter a custom prompt'),
    
    # Content sections in download
    (r'\?\? ORIGINAL TRANSCRIPTION', '📄 ORIGINAL TRANSCRIPTION'),
    (r'\?\? LECTURE NOTES', '📚 LECTURE NOTES'),
    (r'\?\? CUSTOM PROMPT RESULT', '💬 CUSTOM PROMPT RESULT'),
    (r'\?\? SUMMARY', '📝 SUMMARY'),
    (r'\?\? WEB CONTEXT ENRICHMENT', '🌐 WEB CONTEXT ENRICHMENT'),
    
    # UI elements
    (r'\?\? Download All', '⬇️ Download All'),
    (r'\?\? Generate Lecture Notes', '📚 Generate Lecture Notes'),
    (r'\?\? Custom Prompt', '💬 Custom Prompt'),
    (r'\?\? Generate Exam Questions', '📝 Generate Exam Questions'),
    (r'\? Deleting\.\.\.', '🗑️ Deleting...'),
    (r'\?\?\? Delete', '🗑️ Delete'),
    (r'\? Waiting in queue', '⏳ Waiting in queue'),
    (r'\?\? Processing', '⚙️ Processing'),
    (r'\?\? This page will auto-refresh', '🔄 This page will auto-refresh'),
    (r'\?\? Speakers', '👥 Speakers'),
    (r'\?\? Transcription', '📝 Transcription'),
    (r'\?\? Enhancement failed', '⚠️ Enhancement failed'),
    (r'\?\? Translate to', '🌐 Translate to'),
    (r'\?\? Web Context Enrichment', '🌐 Web Context Enrichment'),
    (r'\?\? Model:', '🤖 Model:'),
    (r'\?\? AI Query:', '🔍 AI Query:'),
    (r'\?\? Sources:', '📚 Sources:'),
    (r'\?\? Link', '🔗 Link'),
    (r'\?\? .* Translation:', '🌐 Translation:'),
    (r'\?\? Lecture Notes', '📚 Lecture Notes'),
    (r'\?\? Custom Prompt Result', '💬 Custom Prompt Result'),
    (r'\?\? Your Prompt:', '💭 Your Prompt:'),
    (r'\?\? Exam Questions', '📝 Exam Questions'),
    (r'\?\? Explanation:', '💡 Explanation:'),
    (r'\?\? Transcription Segments', '📋 Transcription Segments'),
    (r'\?\? Apply Custom Prompt', '💬 Apply Custom Prompt'),
    (r'\?\? AI Provider', '🤖 AI Provider'),
    (r'\?\? Model', '🤖 Model'),
    (r'\?\? Cost:', '💰 Cost:'),
    (r'\?\? AI Model', '🤖 AI Model'),
    (r'\?\? Özel Prompt Metni', '💭 Özel Prompt Metni'),
    (r'\?\? Ipucu:', '💡 İpucu:'),
    
    # Model options
    (r'<option value="gemini-2.5-flash">\? Gemini 2.5-Flash</option>', '<option value="gemini-2.5-flash">⚡ Gemini 2.5-Flash</option>'),
    (r'<option value="gemini-2.0-flash">\?\? Gemini 2.0-Flash</option>', '<option value="gemini-2.0-flash">⚡ Gemini 2.0-Flash</option>'),
    (r'<option value="gemini-1.5-pro">\?\? Gemini 1.5-Pro</option>', '<option value="gemini-1.5-pro">✨ Gemini 1.5-Pro</option>'),
    (r'<option value="gemini-1.5-flash">\? Gemini 1.5-Flash</option>', '<option value="gemini-1.5-flash">⚡ Gemini 1.5-Flash</option>'),
    (r'<option value="gpt-4o-mini">\? GPT-4o-mini</option>', '<option value="gpt-4o-mini">🤖 GPT-4o-mini</option>'),
    (r'<option value="gpt-4o">\?\? GPT-4o</option>', '<option value="gpt-4o">🤖 GPT-4o</option>'),
    (r'<option value="gpt-4-turbo">\?\? GPT-4-Turbo</option>', '<option value="gpt-4-turbo">🤖 GPT-4-Turbo</option>'),
    (r'<option value="llama-3.3-70b-versatile">\?\? Llama 3.3 70B</option>', '<option value="llama-3.3-70b-versatile">🦙 Llama 3.3 70B</option>'),
    (r'<option value="llama-3.1-8b-instant">\? Llama 3.1 8B</option>', '<option value="llama-3.1-8b-instant">🦙 Llama 3.1 8B</option>'),
    (r'<option value="llama-3.1-405b-instruct-turbo">\?\? Llama 3.1 405B', '<option value="llama-3.1-405b-instruct-turbo">🦙 Llama 3.1 405B'),
    (r'<option value="llama-3.3-70b-together">\?\? Llama 3.3 70B</option>', '<option value="llama-3.3-70b-together">🦙 Llama 3.3 70B</option>'),
    
    # Credits sidebar
    (r"icon: '\?\?\?'", "icon: '📝'"),  # transcription
    (r"icon: '\?'", "icon: '✨'"),  # ai_enhancement (single ?)
    (r"icon: '\?\?'", "icon: '📚'"),  # lecture_notes (generic ??)
    
    # Operation labels - specific
    (r"transcription: \{ tr: 'Transkripsiyon', en: 'Transcription', icon: '\?\?\?' \}", "transcription: { tr: 'Transkripsiyon', en: 'Transcription', icon: '📝' }"),
    (r"ai_enhancement: \{ tr: 'AI Iyilestirme', en: 'AI Enhancement', icon: '\?' \}", "ai_enhancement: { tr: 'AI Iyilestirme', en: 'AI Enhancement', icon: '✨' }"),
    (r"lecture_notes: \{ tr: 'Ders Notlari', en: 'Lecture Notes', icon: '\?\?' \}", "lecture_notes: { tr: 'Ders Notlari', en: 'Lecture Notes', icon: '📚' }"),
    (r"exam_questions: \{ tr: 'Sinav Sorulari', en: 'Exam Questions', icon: '\?\?' \}", "exam_questions: { tr: 'Sinav Sorulari', en: 'Exam Questions', icon: '📝' }"),
    (r"custom_prompt: \{ tr: '.*zel Prompt', en: 'Custom Prompt', icon: '\?\?' \}", "custom_prompt: { tr: 'Özel Prompt', en: 'Custom Prompt', icon: '💬' }"),
    (r"translation: \{ tr: '.*eviri', en: 'Translation', icon: '\?\?' \}", "translation: { tr: 'Çeviri', en: 'Translation', icon: '🌐' }"),
    
    # Default operation label fallback
    (r"operationLabels\[tx\.operation_type\] \|\| \{ tr: tx\.operation_type, en: tx\.operation_type, icon: '\?\?' \}", "operationLabels[tx.operation_type] || { tr: tx.operation_type, en: tx.operation_type, icon: '📌' }"),
    
    # Model icons based on credit multiplier
    (r"const icon = model\.credit_multiplier >= 2 \? '\?\?' : model\.credit_multiplier > 1 \? '\?' : '\?\?';", "const icon = model.credit_multiplier >= 2 ? '🔥' : model.credit_multiplier > 1 ? '⚡' : '💚';"),
    
    # Misc console logs
    (r'\?\? Topic', '🏷️ Topic'),
    (r'?? ', '🔍 '),  # Generic console.log prefix
    
    # Harcanan Krediler header
    (r"\?\? \{i18n\.language === 'tr' \? 'Harcanan Krediler' : 'Credits Spent'\}", "💳 {i18n.language === 'tr' ? 'Harcanan Krediler' : 'Credits Spent'}"),
    
    # Language emoji
    (r'?? \{transcription\.language\}', '🌐 {transcription.language}'),
    
    # Modal headers
    (r"\{aiAction === 'notes' && '\?\? Generate Lecture Notes'\}", "{aiAction === 'notes' && '📚 Generate Lecture Notes'}"),
    (r"\{aiAction === 'exam' && '\?\? Generate Exam Questions'\}", "{aiAction === 'exam' && '📝 Generate Exam Questions'}"),
]

def fix_emojis():
    """Fix all emoji placeholders in the file"""
    
    # Create backup
    if not os.path.exists(BACKUP_PATH):
        print(f"📦 Creating backup: {BACKUP_PATH}")
        with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Backup created")
    else:
        print("ℹ️ Backup already exists")
    
    # Read file
    print(f"\n📖 Reading file: {FILE_PATH}")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Count initial ?? occurrences
    initial_count = content.count('??')
    print(f"🔍 Found {initial_count} instances of '??'")
    
    # Apply replacements
    replacements_made = 0
    for pattern, replacement in EMOJI_REPLACEMENTS:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            replacements_made += matches
            print(f"  ✓ Replaced {matches} matches for pattern: {pattern[:50]}...")
    
    # Count remaining ?? occurrences
    remaining_count = content.count('??')
    
    # Write back
    print(f"\n💾 Writing changes to file...")
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ EMOJI FIX COMPLETED!")
    print(f"{'='*60}")
    print(f"📊 Initial ?? count: {initial_count}")
    print(f"🔧 Replacements made: {replacements_made}")
    print(f"⚠️ Remaining ?? count: {remaining_count}")
    print(f"📁 Backup saved to: {BACKUP_PATH}")
    
    if remaining_count > 0:
        print(f"\n⚠️ Warning: {remaining_count} ?? placeholders still remain")
        print("These may need manual review or additional patterns")
    else:
        print("\n🎉 All emoji placeholders successfully replaced!")

if __name__ == "__main__":
    fix_emojis()
