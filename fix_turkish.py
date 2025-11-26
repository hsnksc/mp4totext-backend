#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

# Read the file with UTF-8 encoding
with open('temp_admin_page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Turkish character replacements
replacements = {
    'FiyatlandÄ±rma': 'Fiyatlandırma',
    'FiyatlandÄ±rmasÄ±': 'Fiyatlandırması',
    'KullanÄ±cÄ±': 'Kullanıcı',
    'KullanÄ±cÄ±lar': 'Kullanıcılar',
    'YÃ¶netimi': 'Yönetimi',
    'yÃ¶netimi': 'yönetimi',
    'yÃ¶netin': 'yönetin',
    'Ã¶zellikleri': 'özellikleri',
    'yakÄ±nda': 'yakında',
    'YakÄ±nda': 'Yakında',
    'alÄ±namadÄ±': 'alınamadı',
    'GÃ¼ncelleme': 'Güncelleme',
    'baÅŸarÄ±sÄ±z': 'başarısız',
    'baÅŸÄ±': 'başı',
    'Konuşmacı±': 'Konuşmacı',
    'TanÄ±ma': 'Tanıma',
    'Ä°ndirme': 'İndirme',
    'NotlarÄ±': 'Notları',
    'SÄ±nav': 'Sınav',
    'SorularÄ±': 'Soruları',
    'gÃ¼ncellendi': 'güncellendi',
    'YÃ¼kleniyor': 'Yükleniyor',
    'Ä°ÅŸlem': 'İşlem',
    'maliyetlerini': 'maliyetlerini',
    'DÃ¼zenle': 'Düzenle',
    'iÃ§in': 'için',
    'Ã§arpanlarÄ±nÄ±': 'çarpanlarını',
    'VarsayÄ±lan': 'Varsayılan',
    'Ã‡arpanÄ±': 'Çarpanı',
    'AÃ§Ä±klama': 'Açıklama',
    'âœ…': '✅',
}

# Apply all replacements
for old, new in replacements.items():
    content = content.replace(old, new)

# Write back with UTF-8 encoding
with open('temp_admin_page_fixed.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Türkçe karakterler düzeltildi: temp_admin_page_fixed.tsx")
