"""
Fix all page and component exports to default
"""

from pathlib import Path
import re

FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")

FILES_TO_FIX = [
    "src/components/ProtectedRoute.tsx",
    "src/pages/LoginPage.tsx",
    "src/pages/RegisterPage.tsx",
    "src/pages/DashboardPage.tsx",
    "src/pages/TranscriptionsPage.tsx",
    "src/pages/UploadPage.tsx",
    "src/pages/TranscriptionDetailPage.tsx",
]

def fix_export(file_path: Path):
    """Convert 'export const ComponentName: React.FC' to 'export default ComponentName'"""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Find component name from pattern: const ComponentName: React.FC
        match = re.search(r'const (\w+):\s*React\.FC', content)
        if not match:
            print(f"  ⚠️  Could not find component name in {file_path.name}")
            return False
        
        component_name = match.group(1)
        
        # Check if already has default export
        if f'export default {component_name}' in content:
            print(f"  ✓ {file_path.name} already has default export")
            return True
        
        # Remove existing export keyword from const declaration
        content = content.replace(f'export const {component_name}:', f'const {component_name}:')
        
        # Add default export at the end (before last closing brace)
        content = content.rstrip()
        if content.endswith('};'):
            content = content[:-2] + f';\n\nexport default {component_name};\n'
        elif content.endswith(');'):
            content = content + f'\n\nexport default {component_name};\n'
        else:
            content = content + f'\n\nexport default {component_name};\n'
        
        file_path.write_text(content, encoding='utf-8')
        print(f"  ✅ {file_path.name} fixed! (export default {component_name})")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to fix {file_path.name}: {e}")
        return False

def main():
    print("\n🔧 Fixing All Component Exports...")
    print("=" * 60)
    
    success_count = 0
    total_count = len(FILES_TO_FIX)
    
    for file_rel_path in FILES_TO_FIX:
        file_path = FRONTEND_PATH / file_rel_path
        
        if not file_path.exists():
            print(f"  ⚠️  {file_rel_path} not found, skipping...")
            continue
        
        if fix_export(file_path):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Fixed {success_count}/{total_count} files!")
    print("\n📋 Changes:")
    print("   • All components now use 'export default'")
    print("   • Compatible with App.tsx default imports")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
