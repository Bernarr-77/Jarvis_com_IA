import asyncio
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

async def test_generate():
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents='Olá, teste'
        )
        print("✅ gemini-2.5-flash funcionou:", response.text)
    except Exception as e:
        print("❌ falha gemini-2.5-flash:", e)
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents='Olá, teste'
            )
            print("✅ gemini-2.0-flash funcionou:", response.text)
        except Exception as e2:
            print("❌ falha gemini-2.0-flash:", e2)

if __name__ == "__main__":
    asyncio.run(test_generate())
