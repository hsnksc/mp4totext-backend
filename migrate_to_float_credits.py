"""
Credit System Float Migration
==============================
SQLite INTEGER → FLOAT migration for fractional credits (0.5, 0.25, etc.)

Changes:
- users.credits: Integer → Float
- credit_transactions.amount: Integer → Float
- credit_pricing_configs.cost_per_unit: Integer → Float (allows 0.5, 1.5, etc.)
"""

import sqlite3
import os
from pathlib import Path

def migrate_to_float_credits():
    """Migrate credit system from INTEGER to FLOAT"""
    
    # Find database file
    db_path = Path(__file__).parent / "mp4totext.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print(f"🔍 Found database: {db_path}")
    print(f"📊 Size: {os.path.getsize(db_path) / 1024:.1f} KB\n")
    
    # Backup first
    backup_path = db_path.parent / f"mp4totext_backup_before_float_migration.db"
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("="*80)
        print("🔄 MIGRATING TO FLOAT CREDIT SYSTEM")
        print("="*80 + "\n")
        
        # Step 1: Add new FLOAT columns
        print("📝 Step 1: Adding new FLOAT columns...")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN credits_new REAL")
            print("   ✅ users.credits_new (REAL) added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⚠️  users.credits_new already exists")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE credit_transactions ADD COLUMN amount_new REAL")
            print("   ✅ credit_transactions.amount_new (REAL) added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⚠️  credit_transactions.amount_new already exists")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE credit_pricing_configs ADD COLUMN cost_per_unit_new REAL")
            print("   ✅ credit_pricing_configs.cost_per_unit_new (REAL) added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⚠️  credit_pricing_configs.cost_per_unit_new already exists")
            else:
                raise
        
        conn.commit()
        print()
        
        # Step 2: Copy data to new columns
        print("📋 Step 2: Copying data to new FLOAT columns...")
        
        cursor.execute("UPDATE users SET credits_new = CAST(credits AS REAL)")
        users_updated = cursor.rowcount
        print(f"   ✅ Copied {users_updated} user credit balances")
        
        cursor.execute("UPDATE credit_transactions SET amount_new = CAST(amount AS REAL)")
        tx_updated = cursor.rowcount
        print(f"   ✅ Copied {tx_updated} credit transaction amounts")
        
        cursor.execute("UPDATE credit_pricing_configs SET cost_per_unit_new = CAST(cost_per_unit AS REAL)")
        pricing_updated = cursor.rowcount
        print(f"   ✅ Copied {pricing_updated} pricing configurations")
        
        conn.commit()
        print()
        
        # Step 3: Drop old columns and rename new ones
        print("🔄 Step 3: Replacing old INTEGER columns with FLOAT columns...")
        print("   (SQLite doesn't support DROP COLUMN, using recreate strategy)")
        
        # Users table
        print("\n   📊 Recreating users table...")
        cursor.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR NOT NULL UNIQUE,
                username VARCHAR NOT NULL UNIQUE,
                hashed_password VARCHAR NOT NULL,
                full_name VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                is_superuser BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                credits REAL DEFAULT 0  -- Changed from INTEGER to REAL
            )
        """)
        
        cursor.execute("""
            INSERT INTO users_new 
            SELECT id, email, username, hashed_password, full_name, is_active, is_superuser, 
                   created_at, updated_at, credits_new
            FROM users
        """)
        
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        print("   ✅ users table recreated with REAL credits")
        
        # Credit transactions table
        print("\n   💳 Recreating credit_transactions table...")
        cursor.execute("""
            CREATE TABLE credit_transactions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,  -- Changed from INTEGER to REAL
                operation_type VARCHAR(19) NOT NULL,
                description VARCHAR,
                transcription_id INTEGER,
                extra_info VARCHAR,
                balance_after REAL NOT NULL,  -- Changed from INTEGER to REAL
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (transcription_id) REFERENCES transcriptions(id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO credit_transactions_new
            SELECT id, user_id, amount_new, operation_type, description, 
                   transcription_id, extra_info, amount_new, created_at
            FROM credit_transactions
        """)
        
        cursor.execute("DROP TABLE credit_transactions")
        cursor.execute("ALTER TABLE credit_transactions_new RENAME TO credit_transactions")
        print("   ✅ credit_transactions table recreated with REAL amount")
        
        # Credit pricing configs table
        print("\n   💰 Recreating credit_pricing_configs table...")
        cursor.execute("""
            CREATE TABLE credit_pricing_configs_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_key VARCHAR NOT NULL UNIQUE,
                operation_name VARCHAR NOT NULL,
                cost_per_unit REAL NOT NULL,  -- Changed from INTEGER to REAL
                unit_description VARCHAR,
                description VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO credit_pricing_configs_new
            SELECT id, operation_key, operation_name, cost_per_unit_new, 
                   unit_description, description, is_active, created_at, updated_at
            FROM credit_pricing_configs
        """)
        
        cursor.execute("DROP TABLE credit_pricing_configs")
        cursor.execute("ALTER TABLE credit_pricing_configs_new RENAME TO credit_pricing_configs")
        print("   ✅ credit_pricing_configs table recreated with REAL cost_per_unit")
        
        conn.commit()
        print()
        
        # Step 4: Update speaker recognition pricing to 0.5
        print("💵 Step 4: Updating speaker recognition to 0.5 kredi/dakika...")
        cursor.execute("""
            UPDATE credit_pricing_configs 
            SET cost_per_unit = 0.5,
                unit_description = 'dakika başı'
            WHERE operation_key = 'speaker_recognition'
        """)
        print("   ✅ Speaker recognition: 1 → 0.5 kredi/dakika")
        
        conn.commit()
        print()
        
        # Step 5: Verify migration
        print("="*80)
        print("✅ MIGRATION COMPLETE - VERIFICATION")
        print("="*80 + "\n")
        
        # Check users
        cursor.execute("SELECT COUNT(*), SUM(credits), AVG(credits) FROM users")
        user_count, total_credits, avg_credits = cursor.fetchone()
        print(f"👥 Users: {user_count}")
        print(f"   Total credits: {total_credits:.2f}")
        avg_cr = avg_credits if avg_credits is not None else 0.0
        print(f"   Average credits: {avg_cr:.2f}\n")
        
        # Check transactions
        cursor.execute("SELECT COUNT(*), SUM(amount), AVG(amount) FROM credit_transactions")
        tx_count, total_amount, avg_amount = cursor.fetchone()
        print(f"💳 Transactions: {tx_count}")
        tot_amt = total_amount if total_amount is not None else 0.0
        avg_amt = avg_amount if avg_amount is not None else 0.0
        print(f"   Total amount: {tot_amt:.2f}")
        print(f"   Average amount: {avg_amt:.2f}\n")
        
        # Check pricing
        cursor.execute("SELECT operation_key, cost_per_unit, unit_description FROM credit_pricing_configs WHERE is_active = 1")
        pricing = cursor.fetchall()
        print(f"💰 Pricing Configurations ({len(pricing)}):")
        for op_key, cost, unit in pricing:
            print(f"   {op_key}: {cost} {unit}")
        
        print("\n" + "="*80)
        print("🎉 FLOAT MIGRATION SUCCESSFUL!")
        print("="*80)
        print(f"\n📦 Backup saved: {backup_path}")
        print("\n⚠️  IMPORTANT: Restart backend and Celery worker!")
        print("   - Backend: .\\debug_backend_clean.ps1")
        print("   - Celery: .\\start_celery.bat")
        print("="*80 + "\n")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ MIGRATION FAILED: {e}")
        print(f"\n🔄 Database unchanged, backup available: {backup_path}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_to_float_credits()
