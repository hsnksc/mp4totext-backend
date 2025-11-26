from app.api.transcription import router

print("\n🔍 Registered routes in transcription router:")
print("=" * 60)
for route in router.routes:
    methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'N/A'
    print(f"{methods:15} {route.path}")
print("=" * 60)
