"""
Test credit calculation with new pricing
"""
from app.services.credit_service import CreditPricing

pricing = CreditPricing()

# Test AssemblyAI pricing
duration = 53  # seconds
cost = pricing.calculate_transcription_cost(
    duration_seconds=duration,
    enable_diarization=True,
    transcription_provider="assemblyai"
)

print(f"Duration: {duration}s ({duration/60:.2f} minutes)")
print(f"Cost: {cost} credits")
print(f"Expected: {(duration/60) * 1.2:.2f} credits")
print(f"Old price would be: {(duration/60) * 2.0:.2f} credits")
