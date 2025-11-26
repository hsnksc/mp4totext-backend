"""
Test credit history endpoint
"""

from app.database import SessionLocal
from app.models.credit_transaction import CreditTransaction
from app.services.credit_service import get_credit_service

def test_credit_history():
    db = SessionLocal()
    try:
        # Get user ID 1 (hasan)
        user_id = 1
        
        # Get credit service
        credit_service = get_credit_service(db)
        
        # Get transaction history
        print(f"🔍 Fetching transaction history for user {user_id}...")
        transactions = credit_service.get_transaction_history(user_id=user_id, limit=100, offset=0)
        
        print(f"\n📊 Found {len(transactions)} transactions")
        
        if len(transactions) > 0:
            print(f"\n📝 Sample transaction:")
            t = transactions[0]
            print(f"   ID: {t.id}")
            print(f"   Amount: {t.amount}")
            print(f"   Type: {t.operation_type}")
            print(f"   Description: {t.description}")
            print(f"   Balance After: {t.balance_after}")
            print(f"   Created: {t.created_at}")
        
        # Calculate totals
        total_earned = sum(t.amount for t in transactions if t.amount > 0)
        total_spent = abs(sum(t.amount for t in transactions if t.amount < 0))
        current_balance = credit_service.get_balance(user_id)
        
        print(f"\n💰 Summary:")
        print(f"   Total Earned: +{total_earned}")
        print(f"   Total Spent: -{total_spent}")
        print(f"   Current Balance: {current_balance}")
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_credit_history()
