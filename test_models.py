import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def test_live_api(model_name):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    try:
        config = types.LiveConnectConfig(response_modalities=["TEXT"])
        async with client.aio.live.connect(model=model_name, config=config) as session:
            print(f"✅ Success with {model_name}")
            await session.send_client_content(
                turns=types.Content(role="user", parts=[types.Part(text="Olá")]),
                turn_complete=True
            )
            async for msg in session.receive():
                if msg.text:
                    print(f"Res: {msg.text}")
                    break
    except Exception as e:
        print(f"Failed {model_name}: {e}")

async def main():
    models = [
        "gemini-2.0-flash-realtime-exp",
        "gemini-2.0-flash-live",
        "gemini-2.5-flash-live",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]
    for m in models:
        await test_live_api(m)

if __name__ == "__main__":
    asyncio.run(main())
