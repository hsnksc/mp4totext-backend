"""
Update user credits via API
"""
import requests
import sqlite3

API_BASE = "https://api.gistify.pro/api/v1"
SQLITE_PATH = "mp4totext.db"

def get_admin_token():
    """Login as admin"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": "testuser", "password": "TempPass123!"},
        timeout=30
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def get_original_credits():
    """Get original credits from SQLite"""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT username, credits FROM users")
    result = {row['username']: row['credits'] for row in cur.fetchall()}
    conn.close()
    return result

def main():
    print("🔄 Getting original credits from SQLite...")
    original_credits = get_original_credits()
    
    for username, credits in original_credits.items():
        print(f"  • {username}: {credits:.2f} credits")
    
    print("\n⚠️ Note: Credit update requires admin API endpoint")
    print("   You may need to update credits manually in Coolify PostgreSQL")
    print("\n   Or use Coolify Terminal with this SQL:")
    print("   " + "=" * 50)
    
    for username, credits in original_credits.items():
        print(f"   UPDATE users SET credits = {credits} WHERE username = '{username}';")

if __name__ == "__main__":
    main()
