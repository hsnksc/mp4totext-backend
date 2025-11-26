#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix emoji placeholders (??) in TranscriptionDetailPage.tsx
Replace with proper emojis based on context - SIMPLE VERSION
"""

import os

# File path
WEB_DIR = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages"
FILE_PATH = os.path.join(WEB_DIR, "TranscriptionDetailPage.tsx")
BACKUP_PATH = FILE_PATH + ".emoji_backup2"

# Simple string replacements (order matters - more specific first!)
REPLACEMENTS = [
    # Language flags (most specific first)
    ('English</option>', 'English</option>'),  # Already correct
    ('Turkish</option>', 'Turkish</option>'),
    ('German</option>', 'German</option>'),
    ('French</option>', 'French</option>'),
    ('Spanish</option>', 'Spanish</option>'),
    ('Italian</option>', 'Italian</option>'),
    ('Portuguese</option>', 'Portuguese</option>'),
    ('Russian</option>', 'Russian</option>'),
    ('Arabic</option>', 'Arabic</option>'),
    ('Chinese</option>', 'Chinese</option>'),
    ('Japanese</option>', 'Japanese</option>'),
    ('Korean</option>', 'Korean</option>'),
    
    # Provider icons in small buttons
    ('<div className="text-xl">??</div>\n                    <div className="text-sm font-semibold">Gemini</div>', 
     '<div className="text-xl">✨</div>\n                    <div className="text-sm font-semibold">Gemini</div>'),
    ('<div className="text-xl">??</div>\n                    <div className="text-sm font-semibold">OpenAI</div>',
     '<div className="text-xl">🤖</div>\n                    <div className="text-sm font-semibold">OpenAI</div>'),
    ('<div className="text-xl">??</div>\n                    <div className="text-sm font-semibold">Together AI</div>',
     '<div className="text-xl">🚀</div>\n                    <div className="text-sm font-semibold">Together AI</div>'),
    
    # Provider icons in large modal buttons
    ('<div className="text-2xl mb-2">??</div>\n                    <div className="font-semibold text-gray-800">Gemini</div>',
     '<div className="text-2xl mb-2">✨</div>\n                    <div className="font-semibold text-gray-800">Gemini</div>'),
    ('<div className="text-2xl mb-2">??</div>\n                    <div className="font-semibold text-gray-800">OpenAI</div>',
     '<div className="text-2xl mb-2">🤖</div>\n                    <div className="font-semibold text-gray-800">OpenAI</div>'),
    ('<div className="text-2xl mb-2">??</div>\n                    <div className="font-semibold text-gray-800">Together AI</div>',
     '<div className="text-2xl mb-2">🚀</div>\n                    <div className="font-semibold text-gray-800">Together AI</div>'),
    
    # Header icon
    ('<span className="text-4xl">??</span>', '<span className="text-4xl">📄</span>'),
    
    # Provider badges
    ("provider === 'groq' && '? Groq'", "provider === 'groq' && '⚡ Groq'"),
    ("provider === 'openai' && '?? OpenAI'", "provider === 'openai' && '🤖 OpenAI'"),
    ("provider === 'gemini' && '? Gemini'", "provider === 'gemini' && '✨ Gemini'"),
    
    # Model dropdown options
    ('<option value="gemini-2.5-flash">? Gemini 2.5-Flash</option>', '<option value="gemini-2.5-flash">⚡ Gemini 2.5-Flash</option>'),
    ('<option value="gemini-2.0-flash">?? Gemini 2.0-Flash</option>', '<option value="gemini-2.0-flash">⚡ Gemini 2.0-Flash</option>'),
    ('<option value="gemini-1.5-pro">?? Gemini 1.5-Pro</option>', '<option value="gemini-1.5-pro">✨ Gemini 1.5-Pro</option>'),
    ('<option value="gemini-1.5-flash">? Gemini 1.5-Flash</option>', '<option value="gemini-1.5-flash">⚡ Gemini 1.5-Flash</option>'),
    ('<option value="gpt-4o-mini">? GPT-4o-mini</option>', '<option value="gpt-4o-mini">🤖 GPT-4o-mini</option>'),
    ('<option value="gpt-4o">?? GPT-4o</option>', '<option value="gpt-4o">🤖 GPT-4o</option>'),
    ('<option value="gpt-4-turbo">?? GPT-4-Turbo</option>', '<option value="gpt-4-turbo">🤖 GPT-4-Turbo</option>'),
    ('<option value="llama-3.3-70b-versatile">?? Llama 3.3 70B</option>', '<option value="llama-3.3-70b-versatile">🦙 Llama 3.3 70B</option>'),
    ('<option value="llama-3.1-8b-instant">? Llama 3.1 8B</option>', '<option value="llama-3.1-8b-instant">🦙 Llama 3.1 8B</option>'),
    ('<option value="llama-3.1-405b-instruct-turbo">?? Llama 3.1 405B', '<option value="llama-3.1-405b-instruct-turbo">🦙 Llama 3.1 405B'),
    ('<option value="llama-3.3-70b-together">?? Llama 3.3 70B</option>', '<option value="llama-3.3-70b-together">🦙 Llama 3.3 70B</option>'),
    
    # Section headers
    ('?? ORIGINAL TRANSCRIPTION', '📄 ORIGINAL TRANSCRIPTION'),
    ('?? LECTURE NOTES', '📚 LECTURE NOTES'),
    ('?? CUSTOM PROMPT RESULT', '💬 CUSTOM PROMPT RESULT'),
    ('?? SUMMARY', '📝 SUMMARY'),
    ('?? WEB CONTEXT ENRICHMENT', '🌐 WEB CONTEXT ENRICHMENT'),
    
    # Buttons and actions
    ('?? Download All', '⬇️ Download All'),
    ('?? Generate Lecture Notes', '📚 Generate Lecture Notes'),
    ('?? Custom Prompt', '💬 Custom Prompt'),
    ('?? Generate Exam Questions', '📝 Generate Exam Questions'),
    ('? Deleting...', '🗑️ Deleting...'),
    ('??? Delete', '🗑️ Delete'),
    ('? Waiting in queue...', '⏳ Waiting in queue...'),
    ('?? Processing...', '⚙️ Processing...'),
    ('?? This page will auto-refresh', '🔄 This page will auto-refresh'),
    
    # Info labels
    ('?? Speakers', '👥 Speakers'),
    ('?? Transcription', '📝 Transcription'),
    ('?? Enhancement failed', '⚠️ Enhancement failed'),
    ('?? Translate to', '🌐 Translate to'),
    ('?? Web Context Enrichment', '🌐 Web Context Enrichment'),
    ('?? Model:', '🤖 Model:'),
    ('?? AI Query:', '🔍 AI Query:'),
    ('?? Sources:', '📚 Sources:'),
    ('?? Link', '🔗 Link'),
    ('?? Lecture Notes', '📚 Lecture Notes'),
    ('?? Custom Prompt Result', '💬 Custom Prompt Result'),
    ('?? Your Prompt:', '💭 Your Prompt:'),
    ('?? Exam Questions', '📝 Exam Questions'),
    ('?? Explanation:', '💡 Explanation:'),
    ('?? Transcription Segments', '📋 Transcription Segments'),
    ('?? Apply Custom Prompt', '💬 Apply Custom Prompt'),
    ('?? AI Provider', '🤖 AI Provider'),
    ('?? Model', '🤖 Model'),
    ('?? Cost:', '💰 Cost:'),
    ('?? AI Model Seçimi', '🤖 AI Model Seçimi'),
    ('?? Özel Prompt Metni', '💭 Özel Prompt Metni'),
    ('?? Ipucu:', '💡 İpucu:'),
    
    # Translation section
    ('?? {transcription.language}', '🌐 {transcription.language}'),
    
    # Modal titles
    ("{aiAction === 'notes' && '?? Generate Lecture Notes'}", "{aiAction === 'notes' && '📚 Generate Lecture Notes'}"),
    ("{aiAction === 'exam' && '?? Generate Exam Questions'}", "{aiAction === 'exam' && '📝 Generate Exam Questions'}"),
    
    # Operation labels in credit transactions
    ("icon: '???'", "icon: '📝'"),  # transcription (3 question marks)
    ("icon: '?'", "icon: '✨'"),  # ai_enhancement (1 question mark) - MUST BE AFTER LONGER PATTERNS
    ("transcription: { tr: 'Transkripsiyon', en: 'Transcription', icon: '???' }", "transcription: { tr: 'Transkripsiyon', en: 'Transcription', icon: '📝' }"),
    ("ai_enhancement: { tr: 'AI Iyilestirme', en: 'AI Enhancement', icon: '?' }", "ai_enhancement: { tr: 'AI Iyilestirme', en: 'AI Enhancement', icon: '✨' }"),
    ("lecture_notes: { tr: 'Ders Notlari', en: 'Lecture Notes', icon: '??' }", "lecture_notes: { tr: 'Ders Notlari', en: 'Lecture Notes', icon: '📚' }"),
    ("exam_questions: { tr: 'Sinav Sorulari', en: 'Exam Questions', icon: '??' }", "exam_questions: { tr: 'Sinav Sorulari', en: 'Exam Questions', icon: '📝' }"),
    
    # Fallback for operation icons
    ("icon: '??'", "icon: '📌'"),  # Generic fallback
    
    # Credits header
    ("?? {i18n.language === 'tr' ? 'Harcanan Krediler' : 'Credits Spent'}", "💳 {i18n.language === 'tr' ? 'Harcanan Krediler' : 'Credits Spent'}"),
    
    # Model credit multiplier icon calculation
    ("const icon = model.credit_multiplier >= 2 ? '??' : model.credit_multiplier > 1 ? '?' : '??';", 
     "const icon = model.credit_multiplier >= 2 ? '🔥' : model.credit_multiplier > 1 ? '⚡' : '💚';"),
    
    # Console logs (debugging)
    ('?? Component mounted', '🔧 Component mounted'),
    ('?? Making API call', '📡 Making API call'),
    ('?? Pricing response', '💰 Pricing response'),
    ('?? AI Models response', '🤖 AI Models response'),
    ('?? Models count', '📊 Models count'),
    ('?? Polling', '🔄 Polling'),
    ('?? API Response', '📥 API Response'),
    ('?? Full Response Keys', '🔑 Full Response Keys'),
    ('?? Gemini Status', '⚡ Gemini Status'),
    ('?? use_gemini', '🔧 use_gemini'),
    ('?? Loaded', '💳 Loaded'),
    ('?? Please enter a custom prompt', '⚠️ Please enter a custom prompt'),
    ('?? Topic', '🏷️ Topic'),
]

def fix_emojis_simple():
    """Fix all emoji placeholders using simple string replacement"""
    
    # Create backup
    if not os.path.exists(BACKUP_PATH):
        print(f"📦 Creating backup: {BACKUP_PATH}")
        with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Backup created")
    else:
        print("ℹ️ Backup already exists, skipping...")
        with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    
    # Count initial ?? occurrences
    initial_count = content.count('??')
    initial_single = content.count('?') - (initial_count * 2)  # Approximate single ? count
    print(f"\n📖 Reading file: {FILE_PATH}")
    print(f"🔍 Found {initial_count} instances of '??'")
    print(f"🔍 Found ~{initial_single} instances of single '?'")
    
    # Apply replacements
    replacements_made = 0
    for old, new in REPLACEMENTS:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements_made += count
            if '??' in old or '?' in old:
                print(f"  ✓ Replaced {count}x: {old[:60]}...")
    
    # Count remaining ?? occurrences
    remaining_count = content.count('??')
    remaining_single = content.count('?') - (remaining_count * 2)
    
    # Write back
    print(f"\n💾 Writing changes to file...")
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ EMOJI FIX COMPLETED!")
    print(f"{'='*60}")
    print(f"📊 Initial '??' count: {initial_count}")
    print(f"📊 Initial '?' count: ~{initial_single}")
    print(f"🔧 Replacements made: {replacements_made}")
    print(f"⚠️ Remaining '??' count: {remaining_count}")
    print(f"⚠️ Remaining '?' count: ~{remaining_single}")
    print(f"📁 Backup: {BACKUP_PATH}")
    
    if remaining_count > 0 or remaining_single > 10:
        print(f"\n⚠️ Warning: Some placeholders still remain")
        print("Run grep to find them:")
        print("  Select-String -Pattern '\\?\\?' TranscriptionDetailPage.tsx")
    else:
        print("\n🎉 All known emoji placeholders successfully replaced!")

if __name__ == "__main__":
    fix_emojis_simple()
