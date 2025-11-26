"""
Fix console.log spam in TranscriptionDetailPage.tsx
Replaces the problematic console.log line with a commented version
"""

import re

file_path = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages\TranscriptionDetailPage.tsx"

# Read the file with proper encoding handling
encodings = ['utf-8', 'utf-8-sig', 'cp1254', 'latin-1']
content = None

for encoding in encodings:
    try:
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        print(f"✅ File read successfully with {encoding} encoding")
        break
    except Exception as e:
        continue

if content is None:
    print("❌ Failed to read file with any encoding")
    exit(1)

# Find and replace the specific console.log
# Pattern: console.log with Model, Multiplier, Final
pattern = r'(\s+)(console\.log\(`🔍 Model: \$\{model\.model_name\}.*?\);)'

# Replace with commented version
replacement = r'\1// PERFORMANCE FIX: Disabled console spam\n\1// \2'

# Apply replacement
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Check if replacement was made
if new_content != content:
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Console.log spam fixed successfully!")
    print("📝 Line 1765: console.log commented out")
else:
    print("⚠️  Pattern not found - trying alternative method...")
    
    # Alternative: Comment out all console.log lines containing "Model:" and "Multiplier"
    lines = content.split('\n')
    modified = False
    
    for i, line in enumerate(lines):
        if 'console.log' in line and '🔍 Model:' in line and 'Multiplier' in line:
            # Comment out this line
            indentation = len(line) - len(line.lstrip())
            lines[i] = ' ' * indentation + '// PERFORMANCE FIX: ' + line.lstrip()
            modified = True
            print(f"✅ Fixed line {i+1}: {line.strip()[:50]}...")
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("✅ Alternative fix applied successfully!")
    else:
        print("❌ No matching lines found")

print("\n📊 Summary:")
print("- Backup saved as: TranscriptionDetailPage.tsx.backup")
print("- Console spam in model dropdown disabled")
print("- Web app needs restart to apply changes")
