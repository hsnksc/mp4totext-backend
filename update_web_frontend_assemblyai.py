"""
Update Web Frontend TranscriptionDetailPage.tsx
Add missing AssemblyAI features: Entities, Highlights, JSON parsing, better styling
"""

import re
import os

WEB_FILE = r'C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages\TranscriptionDetailPage.tsx'

def update_render_speech_understanding():
    """Update renderSpeechUnderstanding with Entities, Highlights, JSON parsing"""
    
    with open(WEB_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find renderSpeechUnderstanding function
    pattern = r'(const renderSpeechUnderstanding = \(\) => \{.*?)(return \([\s\S]*?)(  \};)'
    
    match = re.search(pattern, content)
    if not match:
        print("❌ Could not find renderSpeechUnderstanding function")
        return
    
    # New implementation with JSON parsing and all features
    new_function = '''const renderSpeechUnderstanding = () => {
    // Helper to parse JSON fields (they might be stored as strings in DB)
    const parseField = (field: any) => {
      if (!field) return null;
      if (typeof field === 'string') {
        try {
          return JSON.parse(field);
        } catch {
          return null;
        }
      }
      return field;
    };

    const sentiment = parseField(transcription?.sentiment_analysis);
    const chapters = parseField(transcription?.auto_chapters);
    const entities = parseField(transcription?.entities);
    const highlights = parseField(transcription?.highlights);

    const hasAnyFeature = sentiment || chapters || entities || highlights;

    if (!hasAnyFeature) {
      return (
        <div className="flex flex-col items-center justify-center py-16 px-6 bg-gray-800/50 rounded-xl border border-gray-700">
          <div className="text-6xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold text-gray-300 mb-2">Analiz Verisi Yok</h3>
          <p className="text-gray-400 text-center max-w-md">
            Bu transkript için Speech Understanding özellikleri aktif değil veya henüz işlenmedi
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Auto Chapters */}
        {chapters && chapters.length > 0 && (
          <div className="bg-gradient-to-br from-emerald-900/20 to-emerald-800/10 rounded-xl p-6 border border-emerald-700/30">
            <h3 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">📚</span> Bölümler ({chapters.length})
            </h3>
            <div className="space-y-4">
              {chapters.map((chapter: any, idx: number) => (
                <div key={idx} className="bg-gray-800/50 rounded-lg p-4 border-l-4 border-emerald-500">
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="text-emerald-300 font-semibold text-base">
                      {chapter.headline || `Bölüm ${idx + 1}`}
                    </h4>
                    <span className="text-emerald-400 text-sm bg-emerald-900/30 px-3 py-1 rounded-full">
                      {Math.floor((chapter.start || 0) / 1000)}s - {Math.floor((chapter.end || 0) / 1000)}s
                    </span>
                  </div>
                  {chapter.gist && (
                    <p className="text-emerald-200 font-medium mb-2 text-sm">{chapter.gist}</p>
                  )}
                  <p className="text-gray-300 text-sm leading-relaxed">{chapter.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sentiment Analysis */}
        {sentiment && sentiment.length > 0 && (
          <div className="bg-gradient-to-br from-purple-900/20 to-purple-800/10 rounded-xl p-6 border border-purple-700/30">
            <h3 className="text-lg font-bold text-purple-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">🎭</span> Duygu Analizi ({sentiment.length})
            </h3>
            <div className="space-y-3">
              {sentiment.map((sent: any, idx: number) => {
                const sentimentColor = sent.sentiment === 'POSITIVE' ? 'emerald' : 
                                       sent.sentiment === 'NEGATIVE' ? 'red' : 'amber';
                const sentimentEmoji = sent.sentiment === 'POSITIVE' ? '😊' : 
                                       sent.sentiment === 'NEGATIVE' ? '😟' : '😐';
                
                return (
                  <div key={idx} className={`bg-gray-800/50 rounded-lg p-4 border-l-4 ${
                    sent.sentiment === 'POSITIVE' ? 'border-emerald-500' :
                    sent.sentiment === 'NEGATIVE' ? 'border-red-500' : 'border-amber-500'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={`font-semibold flex items-center gap-2 ${
                        sent.sentiment === 'POSITIVE' ? 'text-emerald-400' :
                        sent.sentiment === 'NEGATIVE' ? 'text-red-400' : 'text-amber-400'
                      }`}>
                        <span className="text-xl">{sentimentEmoji}</span>
                        {sent.sentiment}
                      </span>
                      <span className={`text-sm px-3 py-1 rounded-full ${
                        sent.sentiment === 'POSITIVE' ? 'text-emerald-400 bg-emerald-900/30' :
                        sent.sentiment === 'NEGATIVE' ? 'text-red-400 bg-red-900/30' : 
                        'text-amber-400 bg-amber-900/30'
                      }`}>
                        {(sent.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-gray-300 text-sm">{sent.text}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Entities */}
        {entities && entities.length > 0 && (
          <div className="bg-gradient-to-br from-violet-900/20 to-violet-800/10 rounded-xl p-6 border border-violet-700/30">
            <h3 className="text-lg font-bold text-violet-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">🏷️</span> İsimler ve Kavramlar ({entities.length})
            </h3>
            <div className="flex flex-wrap gap-2">
              {entities.slice(0, 30).map((entity: any, idx: number) => (
                <div key={idx} className="bg-violet-900/30 px-4 py-2 rounded-full border border-violet-600/40 hover:border-violet-500/60 transition-colors cursor-default">
                  <span className="text-violet-300 font-medium text-sm">{entity.text}</span>
                  <span className="text-violet-400 text-xs ml-2">({entity.entity_type})</span>
                </div>
              ))}
              {entities.length > 30 && (
                <div className="bg-violet-900/30 px-4 py-2 rounded-full border border-violet-600/40">
                  <span className="text-violet-400 text-sm">+{entities.length - 30} more</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Highlights */}
        {highlights && highlights.length > 0 && (
          <div className="bg-gradient-to-br from-amber-900/20 to-amber-800/10 rounded-xl p-6 border border-amber-700/30">
            <h3 className="text-lg font-bold text-amber-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">⭐</span> Önemli Noktalar ({highlights.length})
            </h3>
            <div className="flex flex-wrap gap-3">
              {highlights.map((highlight: any, idx: number) => (
                <div key={idx} className="bg-amber-900/30 px-4 py-2 rounded-full border border-amber-600/40 hover:border-amber-500/60 transition-colors flex items-center gap-2 cursor-default">
                  <span className="text-amber-300 font-semibold text-sm">{highlight.text}</span>
                  {highlight.count > 1 && (
                    <span className="bg-amber-600 text-gray-900 text-xs font-bold px-2 py-0.5 rounded-full">
                      {highlight.count}×
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };'''
    
    # Replace the function
    new_content = re.sub(pattern, new_function + '\n\n  ', content, count=1)
    
    # Write back
    with open(WEB_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Updated renderSpeechUnderstanding with Entities, Highlights, JSON parsing, and beautiful styling!")


def update_render_lemur():
    """Update renderLeMUR with JSON parsing and better styling"""
    
    with open(WEB_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find renderLeMUR function
    pattern = r'(const renderLeMUR = \(\) => \{.*?)(return \([\s\S]*?)(  \};)'
    
    match = re.search(pattern, content)
    if not match:
        print("❌ Could not find renderLeMUR function")
        return
    
    new_function = '''const renderLeMUR = () => {
    // Helper to parse JSON fields
    const parseField = (field: any) => {
      if (!field) return null;
      if (typeof field === 'string') {
        try {
          return JSON.parse(field);
        } catch {
          return field; // Return as-is if not JSON
        }
      }
      return field;
    };

    const summary = parseField(transcription?.lemur_summary);
    const actionItems = parseField(transcription?.lemur_action_items);
    const questionsAnswers = parseField(transcription?.lemur_questions_answers);

    const hasLeMUR = summary || actionItems || questionsAnswers;

    if (!hasLeMUR) {
      return (
        <div className="flex flex-col items-center justify-center py-16 px-6 bg-gray-800/50 rounded-xl border border-gray-700">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-xl font-semibold text-gray-300 mb-2">LeMUR AI Verisi Yok</h3>
          <p className="text-gray-400 text-center max-w-md">
            Bu transkript için LeMUR AI özellikleri aktif değil veya işlem başarısız oldu
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* LeMUR Summary */}
        {summary && (
          <div className="bg-gradient-to-br from-blue-900/20 to-blue-800/10 rounded-xl p-6 border-l-4 border-blue-500">
            <h3 className="text-lg font-bold text-blue-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">📝</span> AI Özeti
            </h3>
            <div className="prose prose-invert prose-slate max-w-none">
              <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                {typeof summary === 'string' ? summary : JSON.stringify(summary, null, 2)}
              </p>
            </div>
          </div>
        )}

        {/* Action Items */}
        {actionItems && (
          <div className="bg-gradient-to-br from-emerald-900/20 to-emerald-800/10 rounded-xl p-6 border border-emerald-700/30">
            <h3 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">✅</span> Yapılacaklar
            </h3>
            <div className="space-y-3">
              {Array.isArray(actionItems) ? (
                actionItems.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-3 bg-gray-800/50 rounded-lg p-4 border-l-4 border-emerald-500">
                    <span className="text-emerald-400 text-xl mt-0.5">✓</span>
                    <p className="text-gray-300 flex-1">
                      {typeof item === 'object' ? (item.text || JSON.stringify(item)) : item}
                    </p>
                  </div>
                ))
              ) : typeof actionItems === 'object' && actionItems.items ? (
                actionItems.items.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-3 bg-gray-800/50 rounded-lg p-4 border-l-4 border-emerald-500">
                    <span className="text-emerald-400 text-xl">✓</span>
                    <p className="text-gray-300 flex-1">{item}</p>
                  </div>
                ))
              ) : (
                <p className="text-gray-300 whitespace-pre-wrap">
                  {typeof actionItems === 'string' ? actionItems : JSON.stringify(actionItems, null, 2)}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Q&A */}
        {questionsAnswers && Array.isArray(questionsAnswers) && questionsAnswers.length > 0 && (
          <div className="bg-gradient-to-br from-amber-900/20 to-amber-800/10 rounded-xl p-6 border border-amber-700/30">
            <h3 className="text-lg font-bold text-amber-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">❓</span> Sorular ve Cevaplar ({questionsAnswers.length})
            </h3>
            <div className="space-y-4">
              {questionsAnswers.map((qa: any, idx: number) => (
                <div key={idx} className="bg-gray-800/50 rounded-lg p-5 border-l-4 border-amber-500">
                  <p className="text-amber-300 font-semibold mb-3 text-base flex items-start gap-2">
                    <span className="text-lg">❓</span>
                    <span>{qa.question}</span>
                  </p>
                  <p className="text-gray-300 leading-relaxed pl-7">
                    {qa.answer}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };'''
    
    # Replace the function
    new_content = re.sub(pattern, new_function + '\n\n  ', content, count=1)
    
    # Write back
    with open(WEB_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Updated renderLeMUR with JSON parsing and improved styling!")


def main():
    print("=" * 80)
    print("🚀 WEB FRONTEND UPDATE - AssemblyAI Speech Understanding + LeMUR")
    print("=" * 80)
    print()
    
    if not os.path.exists(WEB_FILE):
        print(f"❌ File not found: {WEB_FILE}")
        return
    
    print(f"📝 Updating {os.path.basename(WEB_FILE)}...")
    print()
    
    # Backup first
    backup_file = WEB_FILE + '.assemblyai_backup'
    with open(WEB_FILE, 'r', encoding='utf-8') as f:
        original_content = f.read()
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"💾 Backup created: {os.path.basename(backup_file)}")
    print()
    
    try:
        update_render_speech_understanding()
        update_render_lemur()
        
        print()
        print("=" * 80)
        print("✅ WEB FRONTEND UPDATED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📋 NEW FEATURES ADDED:")
        print("  ✓ 📚 Auto Chapters with gist, headline, summary")
        print("  ✓ 🎭 Sentiment Analysis with emoji and colors")
        print("  ✓ 🏷️ Entities (Names, Places, Organizations)")
        print("  ✓ ⭐ Highlights (Important Points)")
        print("  ✓ 📝 LeMUR Summary")
        print("  ✓ ✅ Action Items")
        print("  ✓ ❓ Questions & Answers")
        print("  ✓ JSON parsing for database string fields")
        print("  ✓ Beautiful gradient styling matching mobile")
        print()
        print("🌐 Test at: http://localhost:5173")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   Restoring backup...")
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        with open(WEB_FILE, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        print(f"   ✓ Backup restored")


if __name__ == "__main__":
    main()
