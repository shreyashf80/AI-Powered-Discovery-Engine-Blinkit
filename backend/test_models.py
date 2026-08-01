import os
from google import genai
client = genai.Client(api_key="YOUR_GEMINI_API_KEY")
try:
    response = client.models.generate_content(model="gemini-flash-latest", contents="hello")
    print("first key gemini-flash-latest worked")
except Exception as e:
    print(f"first key failed: {e}")
