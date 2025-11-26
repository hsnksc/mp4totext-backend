import sqlite3

conn = sqlite3.connect('mp4totext.db')
c = conn.cursor()

tables = ['users_new', 'credit_transactions_new', 'credit_pricing_configs_new']
for t in tables:
    c.execute(f'DROP TABLE IF EXISTS {t}')
    print(f'✅ Dropped {t}')

conn.commit()
conn.close()
print('\n✅ Cleanup complete')
