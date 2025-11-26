"""
Fix web frontend by properly replacing render functions
"""

WEB_FILE = r'C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages\TranscriptionDetailPage.tsx'

# Read all lines
with open(WEB_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print(f"Line 228 (renderSpeechUnderstanding start): {lines[227][:50]}")
print(f"Line 322 (renderLeMUR start): {lines[321][:50]}")

# Find where renderSpeechUnderstanding ends (before renderLeMUR)
# Line 228 to line 321 (before line 322)
speech_start = 227  # 0-indexed
speech_end = 321    # exclusive (line 322 is where renderLeMUR starts)

# Find where renderLeMUR ends (look for next const function)
lemur_start = 321
# Find next function after renderLeMUR
lemur_end = None
for i in range(lemur_start + 1, len(lines)):
    if lines[i].strip().startswith('const ') and '= (' in lines[i]:
        lemur_end = i
        print(f"Next function after renderLeMUR at line {i+1}: {lines[i][:50]}")
        break

if not lemur_end:
    print("ERROR: Could not find end of renderLeMUR")
    exit(1)

# NEW renderSpeechUnderstanding (with proper closing)
NEW_SPEECH = '''  const renderSpeechUnderstanding = () => {
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

    if (!sentiment && !chapters && !entities && !highlights) {
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

        {sentiment && sentiment.length > 0 && (
          <div className="bg-gradient-to-br from-purple-900/20 to-purple-800/10 rounded-xl p-6 border border-purple-700/30">
            <h3 className="text-lg font-bold text-purple-400 mb-4 flex items-center gap-2">
              <span className="text-2xl">🎭</span> Duygu Analizi ({sentiment.length})
            </h3>
            <div className="space-y-3">
              {sentiment.map((sent: any, idx: number) => {
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
                  <span className="text-violet-400 text-sm">+{entities.length - 30} daha</span>
                </div>
              )}
            </div>
          </div>
        )}

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
  };

'''

# NEW renderLeMUR (with proper closing)
NEW_LEMUR = '''  const renderLeMUR = () => {
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

    const summary = parseField(transcription?.lemur_summary);
    const actionItems = parseField(transcription?.lemur_action_items);
    const questionsAnswers = parseField(transcription?.lemur_questions_answers);

    if (!summary && !actionItems && !questionsAnswers) {
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
  };

'''

# Build new content
new_lines = (
    lines[:speech_start] +  # Everything before renderSpeechUnderstanding
    NEW_SPEECH.split('\n') +  # New renderSpeechUnderstanding
    ['\n'] +
    NEW_LEMUR.split('\n') +  # New renderLeMUR
    ['\n'] +
    lines[lemur_end:]  # Everything after old renderLeMUR
)

# Write
with open(WEB_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join([line.rstrip() for line in new_lines]))

print("✅ File updated successfully!")
print(f"   Removed lines {speech_start+1}-{lemur_end}")
print(f"   Inserted new renderSpeechUnderstanding and renderLeMUR")

# Verify braces
with open(WEB_FILE, 'r', encoding='utf-8') as f:
    content = f.read()
    open_braces = content.count('{')
    close_braces = content.count('}')
    print(f"\n📊 Brace check:")
    print(f"   Open: {open_braces}")
    print(f"   Close: {close_braces}")
    print(f"   Difference: {open_braces - close_braces}")
    
    if open_braces == close_braces:
        print("✅ Braces balanced!")
    else:
        print("⚠️ Brace mismatch detected")
