"""
Force Vite to clear cache and rebuild
"""

from pathlib import Path
import shutil

FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")
NODE_MODULES_CACHE = FRONTEND_PATH / "node_modules" / ".vite"

def main():
    print("\n🔧 Clearing Vite Cache...")
    print("=" * 50)
    
    # Clear Vite cache
    if NODE_MODULES_CACHE.exists():
        print(f"📂 Found Vite cache at: {NODE_MODULES_CACHE}")
        try:
            shutil.rmtree(NODE_MODULES_CACHE)
            print("✅ Vite cache cleared!")
        except Exception as e:
            print(f"⚠️  Could not delete cache: {e}")
    else:
        print("ℹ️  No Vite cache found (this is fine)")
    
    print("\n📋 Next steps:")
    print("   1. Vite will be restarted")
    print("   2. Open browser and press CTRL+SHIFT+R (hard refresh)")
    print("   3. Or clear browser cache completely")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
