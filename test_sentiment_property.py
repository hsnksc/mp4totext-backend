"""Test AssemblyAI sentiment_analysis property name"""
import assemblyai as aai

# Check what property name is actually used
print("=== AssemblyAI Transcript Properties ===")
print("Checking if 'sentiment_analysis' exists as property...")

# Mock transcript to see available attributes
from assemblyai import Transcript
print("\nAvailable Transcript attributes:")
attrs = [attr for attr in dir(Transcript) if not attr.startswith('_')]
sentiment_attrs = [attr for attr in attrs if 'sentiment' in attr.lower()]
print(f"Sentiment-related attributes: {sentiment_attrs}")

print("\n=== According to docs ===")
print("Python SDK property: transcript.sentiment_analysis")
print("REST API response: sentiment_analysis_results")
