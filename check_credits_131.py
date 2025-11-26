from app.database import SessionLocal
from app.models.credit_transaction import CreditTransaction

db = SessionLocal()
txs = db.query(CreditTransaction).filter_by(transcription_id=131).all()

print('\n💳 Transkripsiyon #131 Kredi İşlemleri:\n')
for tx in txs:
    print(f'{tx.created_at.strftime("%Y-%m-%d %H:%M")} | {tx.operation_type.value:20} | {tx.amount:8.2f} kredi | {tx.description}')

print(f'\n📊 Toplam: {sum(tx.amount for tx in txs):.2f} kredi\n')
db.close()
