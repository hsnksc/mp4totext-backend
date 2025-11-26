"""Replace all temperature=0.3 with temperature=self._get_temperature() in gemini_service.py"""
import re

file_path = "app/services/gemini_service.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace all instances of temperature=0.3 with temperature=self._get_temperature()
# But skip the ones inside the _get_temperature method itself
original_count = content.count("temperature=0.3")
content = re.sub(r"temperature=0\.3", "temperature=self._get_temperature()", content)
new_count = content.count("temperature=self._get_temperature()")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ Replaced {original_count} occurrences of temperature=0.3")
print(f"📊 Now {new_count} occurrences of temperature=self._get_temperature()")
print(f"🔧 File updated: {file_path}")
