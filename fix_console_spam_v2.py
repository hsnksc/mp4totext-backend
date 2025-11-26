"""
Fix console.log spam - Direct line replacement approach
"""

file_path = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web\src\pages\TranscriptionDetailPage.tsx"

# Read file
with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

print(f"📄 Total lines: {len(lines)}")

# Find lines around 1765 containing console.log
modified = False
for i in range(max(0, 1760), min(len(lines), 1775)):
    line = lines[i]
    
    # Check if this line contains the problematic console.log
    if 'console.log' in line and 'Model:' in line:
        print(f"\n🔍 Found at line {i+1}:")
        print(f"   Original: {line.strip()[:80]}...")
        
        # Get indentation
        indent = len(line) - len(line.lstrip())
        
        # Comment it out
        lines[i] = ' ' * indent + '// PERFORMANCE FIX: Disabled console spam\n' + ' ' * indent + '// ' + line.lstrip()
        
        print(f"   ✅ Commented out successfully")
        modified = True

if modified:
    # Write back
    with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
        f.writelines(lines)
    
    print(f"\n✅ File updated successfully!")
    print("📝 Console.log spam disabled on line ~1765")
    print("\n🔄 Next steps:")
    print("   1. Restart web development server")
    print("   2. Test custom prompt input")
    print("   3. Verify console is clean")
else:
    print("\n❌ No matching console.log found")
    print("💡 Searching for all console.log occurrences...")
    
    for i, line in enumerate(lines):
        if 'console.log' in line and ('Model' in line or 'model' in line):
            print(f"   Line {i+1}: {line.strip()[:60]}...")
