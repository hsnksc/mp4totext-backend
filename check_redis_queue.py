"""Check Redis queue status"""
import redis

# Connect to broker database (1) WITH PASSWORD
r = redis.Redis(host='localhost', port=6379, password='dev_redis_123', db=1, decode_responses=True)

print("=== REDIS BROKER (DB 1) ===")
print(f"Keys count: {r.dbsize()}")

# List all keys
keys = r.keys('*')
if keys:
    print(f"\nKeys found: {len(keys)}")
    for key in keys[:20]:  # Show first 20
        key_type = r.type(key)
        print(f"  {key} ({key_type})")
        
        # If it's a list (queue), show length
        if key_type == 'list':
            length = r.llen(key)
            print(f"    -> Length: {length}")
else:
    print("No keys found!")

# Check for 'high' queue specifically
high_queue = 'high'
if r.exists(high_queue):
    print(f"\n✅ Queue '{high_queue}' exists!")
    print(f"   Length: {r.llen(high_queue)}")
else:
    print(f"\n⚠️ Queue '{high_queue}' does NOT exist!")

print("\n=== RESULTS BACKEND (DB 2) ===")
r2 = redis.Redis(host='localhost', port=6379, password='dev_redis_123', db=2, decode_responses=True)
print(f"Keys count: {r2.dbsize()}")
