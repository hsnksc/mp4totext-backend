import sqlite3

conn = sqlite3.connect('mp4totext.db')
cursor = conn.cursor()

# Get basic info
cursor.execute('''
    SELECT 
        id, 
        filename, 
        use_gemini_enhancement, 
        gemini_status,
        LENGTH(text) as text_len,
        LENGTH(enhanced_text) as enhanced_len,
        text = enhanced_text as are_same
    FROM transcriptions 
    WHERE id = 25
''')

row = cursor.fetchone()

if row:
    print('\n📊 TRANSCRIPTION 25 DURUMU:\n')
    print(f'ID: {row[0]}')
    print(f'Dosya: {row[1]}')
    print(f'Gemini Aktif: {row[2]}')
    print(f'Gemini Status: {row[3]}')
    print(f'Text Uzunluk: {row[4]} karakter')
    print(f'Enhanced Text Uzunluk: {row[5]} karakter')
    print(f'İkisi Aynı mı?: {"EVET ❌" if row[6] else "HAYIR ✅"}')
    
    # Get text samples
    cursor.execute('SELECT text, enhanced_text FROM transcriptions WHERE id = 25')
    row = cursor.fetchone()
    
    text_sample = row[0][:300] if row[0] else "BOŞ"
    enhanced_sample = row[1][:300] if row[1] else "BOŞ"
    
    print(f'\n📝 TEXT (İlk 300 karakter):')
    print(f'{text_sample}...\n')
    
    print(f'✨ ENHANCED TEXT (İlk 300 karakter):')
    print(f'{enhanced_sample}...\n')
    
    if row[0] == row[1]:
        print('⚠️  SORUN: Text ve Enhanced Text TAMAMEN AYNI!')
        print('   Gemini enhancement çalışmadı veya safety filter engelledi.')
    else:
        print('✅ Text ve Enhanced Text FARKLI - Gemini çalıştı!')
else:
    print('❌ Transcription 25 bulunamadı!')

conn.close()
