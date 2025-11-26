import re

text = """
Almanya'daki İAA forında Tevon Feinin tanıtılmasının ardından uygun fiyatlı 
yeni modeli içinde marka CEO'su Türkiye pazarında da satışa sunulacağını duyurdu.
T8X modeli elektrikli SUV segmentinde yer alacak.
"""

# Test sentence splitting
sentences = re.split(r'[.!?]+', text)
print("Sentences found:")
for i, sent in enumerate(sentences):
    sent = sent.strip()
    print(f"{i}: [{len(sent)} chars] {sent[:100]}")
