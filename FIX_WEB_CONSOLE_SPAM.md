# Web Console Spam Düzeltme Kılavuzu

## Sorun
`TranscriptionDetailPage.tsx:1765` satırında her karakter girişinde 41 model için log basılıyor.
Bu console'u spam yapıyor ve performansı düşürüyor.

## Çözüm Adımları

### 1. Console.log'ları Kaldır

**Dosya**: `mp4totext-web/src/pages/TranscriptionDetailPage.tsx`
**Satır**: ~1765

```typescript
// ❌ KALDIRIN - Bu satırları bulun ve silin/yorumlayın
console.log(`🔍 Model: ${model.name}, Base: ${basePrice}, Multiplier: ${model.credit_multiplier}, Final: ${finalPrice}`);
```

**Değiştirin**:
```typescript
// Tamamen kaldır VEYA sadece hata durumunda log:
if (finalPrice < 0 || isNaN(finalPrice)) {
  console.error('Invalid price calculation:', { model: model.name, basePrice, multiplier: model.credit_multiplier });
}
```

### 2. Performans İyileştirmesi - useMemo Ekle

```typescript
import { useMemo } from 'react';

// Model fiyat hesaplamalarını cache'le
const calculatedModels = useMemo(() => {
  if (!models || !basePrice) return [];
  
  return models.map(model => ({
    ...model,
    finalPrice: basePrice * (model.credit_multiplier || 1)
  }));
}, [models, basePrice]);
```

### 3. Input Debounce (Opsiyonel ama Önerilen)

```typescript
import { useState, useCallback } from 'react';
import { debounce } from 'lodash'; // veya kendi debounce fonksiyonunuz

const [customPrompt, setCustomPrompt] = useState('');

// Debounced setter
const debouncedSetPrompt = useCallback(
  debounce((value: string) => {
    setCustomPrompt(value);
    // Fiyat hesaplaması veya API çağrısı burada
  }, 300),
  []
);

// Input onChange'de kullan
<textarea 
  onChange={(e) => debouncedSetPrompt(e.target.value)}
  placeholder="Enter custom prompt..."
/>
```

### 4. Geliştirme Modu Log Guard'ı

```typescript
// Sadece development'ta önemli log'ları tut
if (process.env.NODE_ENV === 'development') {
  console.log('📊 Models count:', models.length);
  console.log('✅ Default model set:', defaultModel);
}

// Production'da hiç log olmaması için
const isDev = process.env.NODE_ENV === 'development';

isDev && console.log('🔍 Model calculation details:', {
  totalModels: models.length,
  basePrice,
  sampleModel: models[0]
});
```

## Öncelik Sırası

1. **URGENT** - Line 1765'teki log'ları kaldır (5 saniye)
2. **HIGH** - useMemo ekle (2 dakika)
3. **MEDIUM** - Debounce ekle (5 dakika)
4. **LOW** - Dev mode guard'ları ekle (10 dakika)

## Test

Düzeltme sonrası:
1. Web uygulamasını yeniden başlat
2. Custom prompt tab'ına git
3. Hızlıca yazı yaz
4. Console'u kontrol et → Log flood olmamalı ✅
5. Performance tab'ı kontrol et → Render süreleri düşmeli ✅

## Kod Arama

Bu satırları bulmak için:
```bash
cd mp4totext-web
grep -n "Model:.*Multiplier" src/**/*.tsx
grep -n "🔍 Model:" src/**/*.tsx
grep -n "console.log" src/pages/TranscriptionDetailPage.tsx | head -20
```

## Sonuç

Bu düzeltme sonrası:
- ✅ Console temiz kalacak
- ✅ Her karakter girişinde 2000+ log yerine 0 log
- ✅ UI daha responsive olacak
- ✅ Browser memory kullanımı düşecek
