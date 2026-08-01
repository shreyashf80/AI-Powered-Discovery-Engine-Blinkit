import asyncio
from google import genai
from src.shared.config import config

async def test():
    client = genai.Client(api_key=config.GEMINI_API_KEYS.split(",")[0])
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents="hello"
        )
        print("Success", response.text)
    except Exception as e:
        print("Error:", type(e), e)

asyncio.run(test())
