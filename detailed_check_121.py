"""Detailed transcription 121 analysis"""
from app.database import SessionLocal
from app.models.transcription import Transcription

def analyze_text_differences(text1, text2, sample_size=500):
    """Find differences between two texts"""
    differences = []
    
    # Compare in chunks
    for i in range(0, min(len(text1), len(text2), 3000), sample_size):
        chunk1 = text1[i:i+sample_size]
        chunk2 = text2[i:i+sample_size]
        
        if chunk1 != chunk2:
            differences.append({
                'position': i,
                'original': chunk1[:200],
                'enhanced': chunk2[:200]
            })
    
    return differences

db = SessionLocal()
t = db.query(Transcription).filter_by(id=121).first()

if not t:
    print("❌ Transcription 121 not found!")
    exit()

print("=" * 80)
print(f"📋 TRANSCRIPTION #{t.id} DETAILED ANALYSIS")
print("=" * 80)
print()

print("🔧 CONFIGURATION")
print(f"  AI Provider: {t.ai_provider}")
print(f"  AI Model: {t.ai_model}")
print(f"  Status: {t.status}")
print(f"  Use Gemini Enhancement: {t.use_gemini_enhancement}")
print()

print("📊 TEXT STATISTICS")
print(f"  Original text length: {len(t.text) if t.text else 0:,}")
print(f"  Enhanced text length: {len(t.enhanced_text) if t.enhanced_text else 0:,}")
print(f"  Cleaned text length: {len(t.cleaned_text) if t.cleaned_text else 0:,}")
print(f"  Texts are identical: {t.text == t.enhanced_text}")
print()

if t.text and t.enhanced_text:
    # Find specific differences
    print("🔍 SEARCHING FOR DIFFERENCES...")
    print()
    
    # Word-level comparison in first 1000 chars
    original_words = t.text[:1000].split()
    enhanced_words = t.enhanced_text[:1000].split()
    
    differences_found = []
    for i, (orig, enh) in enumerate(zip(original_words, enhanced_words)):
        if orig != enh:
            differences_found.append({
                'word_index': i,
                'original': orig,
                'enhanced': enh
            })
    
    if differences_found:
        print(f"✅ FOUND {len(differences_found)} WORD DIFFERENCES in first 1000 chars:")
        print()
        for diff in differences_found[:10]:  # Show first 10
            print(f"  Word #{diff['word_index']}:")
            print(f"    Original: {diff['original']}")
            print(f"    Enhanced: {diff['enhanced']}")
            print()
    else:
        print("⚠️ NO word differences found in first 1000 characters")
        print()
    
    # Character-level comparison
    char_diff_count = sum(1 for c1, c2 in zip(t.text, t.enhanced_text) if c1 != c2)
    print(f"📝 Character differences: {char_diff_count}")
    print()
    
    # Show first 300 characters of each
    print("=" * 80)
    print("📄 TEXT SAMPLES (First 300 characters)")
    print("=" * 80)
    print()
    print("ORIGINAL:")
    print("-" * 80)
    print(t.text[:300])
    print()
    print("ENHANCED:")
    print("-" * 80)
    print(t.enhanced_text[:300])
    print()
    
    # Show samples around character 500, 1000, 1500
    for pos in [500, 1000, 1500]:
        if len(t.text) > pos and len(t.enhanced_text) > pos:
            print(f"=" * 80)
            print(f"📄 TEXT SAMPLES (Position {pos}, 150 chars)")
            print("=" * 80)
            print()
            print("ORIGINAL:")
            print("-" * 80)
            print(t.text[pos:pos+150])
            print()
            print("ENHANCED:")
            print("-" * 80)
            print(t.enhanced_text[pos:pos+150])
            print()

db.close()
