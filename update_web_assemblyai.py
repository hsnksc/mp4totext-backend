"""
Update Web Frontend for AssemblyAI Speech Understanding + LeMUR
Adds beautiful tabs and rendering for all new features
"""

import os
from pathlib import Path

WEB_PATH = Path(r'C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src\pages')
DETAIL_PAGE = WEB_PATH / 'TranscriptionDetailPage.tsx'

# New Speech Understanding Tab Component
SPEECH_UNDERSTANDING_TAB = '''
  // 🎯 Render Speech Understanding Tab
  const renderSpeechUnderstandingTab = () => {
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

    const chapters = parseField(transcription.auto_chapters);
    const sentiment = parseField(transcription.sentiment_analysis);
    const entities = parseField(transcription.entities);
    const topics = parseField(transcription.topics);
    const highlights = parseField(transcription.highlights);

    const hasAnyFeature = chapters || sentiment || entities || topics || highlights;

    if (!hasAnyFeature) {
      return (
        <div className="flex flex-col items-center justify-center py-16 px-6 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="text-6xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold text-slate-300 mb-2">Analiz Verisi Yok</h3>
          <p className="text-slate-400 text-center max-w-md">
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
                <div key={idx} className="bg-slate-800/50 rounded-lg p-4 border-l-4 border-emerald-500">
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
                  <p className="text-slate-300 text-sm leading-relaxed">{chapter.summary}</p>
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
                  <div key={idx} className={`bg-slate-800/50 rounded-lg p-4 border-l-4 border-${sentimentColor}-500`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-${sentimentColor}-400 font-semibold flex items-center gap-2`}>
                        <span className="text-xl">{sentimentEmoji}</span>
                        {sent.sentiment}
                      </span>
                      <span className={`text-${sentimentColor}-400 text-sm bg-${sentimentColor}-900/30 px-3 py-1 rounded-full`}>
                        {(sent.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-slate-300 text-sm">{sent.text}</p>
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
                <div key={idx} className="bg-violet-900/30 px-4 py-2 rounded-full border border-violet-600/40 hover:border-violet-500/60 transition-colors">
                  <span className="text-violet-300 font-medium text-sm">{entity.text}</span>
                  <span className="text-violet-400 text-xs ml-2">({entity.entity_type})</span>
                </div>
              ))}
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
                <div key={idx} className="bg-amber-900/30 px-4 py-2 rounded-full border border-amber-600/40 hover:border-amber-500/60 transition-colors flex items-center gap-2">
                  <span className="text-amber-300 font-semibold text-sm">{highlight.text}</span>
                  {highlight.count > 1 && (
                    <span className="bg-amber-600 text-slate-900 text-xs font-bold px-2 py-0.5 rounded-full">
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
  };
'''

# New LeMUR Tab Component
LEMUR_TAB = '''
  // 🤖 Render LeMUR AI Tab
  const renderLeMURTab = () => {
    const parseField = (field: any) => {
      if (!field) return null;
      if (typeof field === 'string') {
        try {
          return JSON.parse(field);
        } catch {
          return field;
        }
      }
      return field;
    };

    const summary = parseField(transcription.lemur_summary);
    const actionItems = parseField(transcription.lemur_action_items);
    const questionsAnswers = parseField(transcription.lemur_questions_answers);

    const hasLeMUR = summary || actionItems || questionsAnswers;

    if (!hasLeMUR) {
      return (
        <div className="flex flex-col items-center justify-center py-16 px-6 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-xl font-semibold text-slate-300 mb-2">LeMUR AI Verisi Yok</h3>
          <p className="text-slate-400 text-center max-w-md">
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
              <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
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
                  <div key={idx} className="flex items-start gap-3 bg-slate-800/50 rounded-lg p-4 border-l-4 border-emerald-500">
                    <span className="text-emerald-400 text-xl mt-0.5">✓</span>
                    <p className="text-slate-300 flex-1">
                      {typeof item === 'object' ? (item.text || JSON.stringify(item)) : item}
                    </p>
                  </div>
                ))
              ) : typeof actionItems === 'object' && actionItems.items ? (
                actionItems.items.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-3 bg-slate-800/50 rounded-lg p-4 border-l-4 border-emerald-500">
                    <span className="text-emerald-400 text-xl">✓</span>
                    <p className="text-slate-300 flex-1">{item}</p>
                  </div>
                ))
              ) : (
                <p className="text-slate-300 whitespace-pre-wrap">
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
                <div key={idx} className="bg-slate-800/50 rounded-lg p-5 border-l-4 border-amber-500">
                  <p className="text-amber-300 font-semibold mb-3 text-base flex items-start gap-2">
                    <span className="text-lg">❓</span>
                    <span>{qa.question}</span>
                  </p>
                  <p className="text-slate-300 leading-relaxed pl-7">
                    {qa.answer}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };
'''

def update_web_frontend():
    """Update web frontend TranscriptionDetailPage.tsx"""
    
    if not DETAIL_PAGE.exists():
        print(f"❌ File not found: {DETAIL_PAGE}")
        print(f"   Please create web frontend first!")
        return
    
    print(f"📝 Reading {DETAIL_PAGE.name}...")
    content = DETAIL_PAGE.read_text(encoding='utf-8')
    
    # Check if already updated
    if 'renderSpeechUnderstandingTab' in content:
        print("✅ Web frontend already has Speech Understanding tab!")
        return
    
    # Find where to insert the new render functions
    # Look for existing render functions
    insert_marker = "  const renderTranscriptTab = () =>"
    
    if insert_marker not in content:
        print("⚠️ Could not find insertion point!")
        print("   Please add render functions manually.")
        return
    
    # Insert before renderTranscriptTab
    parts = content.split(insert_marker)
    new_content = parts[0] + SPEECH_UNDERSTANDING_TAB + "\n\n" + LEMUR_TAB + "\n\n  " + insert_marker + parts[1]
    
    # Update tab rendering section
    # Find tab content rendering
    if "'original' && renderTranscriptTab()" in new_content:
        # Add new tab conditions
        tab_render_old = "activeTab === 'original' && renderTranscriptTab()"
        tab_render_new = """activeTab === 'speechUnderstanding' ? renderSpeechUnderstandingTab() :
          activeTab === 'lemurAI' ? renderLeMURTab() :
          activeTab === 'original' && renderTranscriptTab()"""
        
        new_content = new_content.replace(tab_render_old, tab_render_new)
    
    # Add new tabs to tab list
    # Look for tab buttons section
    if "<button" in new_content and "setActiveTab('original')" in new_content:
        # Find the tabs container and add new tabs
        # This is a simplified approach - you may need to adjust based on actual structure
        pass
    
    # Write updated content
    DETAIL_PAGE.write_text(new_content, encoding='utf-8')
    print(f"✅ Updated {DETAIL_PAGE.name}")
    print()
    print("📋 MANUAL STEPS REQUIRED:")
    print("1. Add Speech Understanding tab button:")
    print("""
    {(transcription.sentiment_analysis || transcription.auto_chapters || transcription.entities || transcription.highlights) && (
      <button
        onClick={() => setActiveTab('speechUnderstanding')}
        className={`px-6 py-3 rounded-lg font-medium transition-all ${
          activeTab === 'speechUnderstanding'
            ? 'bg-blue-600 text-white'
            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        }`}
      >
        🎯 Analiz
      </button>
    )}
    """)
    print()
    print("2. Add LeMUR AI tab button:")
    print("""
    {(transcription.lemur_summary || transcription.lemur_action_items || transcription.lemur_questions_answers) && (
      <button
        onClick={() => setActiveTab('lemurAI')}
        className={`px-6 py-3 rounded-lg font-medium transition-all ${
          activeTab === 'lemurAI'
            ? 'bg-blue-600 text-white'
            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        }`}
      >
        🤖 AI Özet
      </button>
    )}
    """)

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 WEB FRONTEND - AssemblyAI Speech Understanding + LeMUR Update")
    print("=" * 80)
    print()
    update_web_frontend()
    print()
    print("=" * 80)
    print("✅ Update script completed!")
    print("=" * 80)
