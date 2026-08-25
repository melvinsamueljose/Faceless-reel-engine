import os
import asyncio
import requests
from playwright.async_api import async_playwright
import google.generativeai as genai
import edge_tts

TOOL_URL = os.getenv("TOOL_URL", "https://aicarousels.com")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

async def record_screen():
    print(f"[1/4] Recording screen for {TOOL_URL}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1080, 'height': 1920},
            record_video_dir="output/",
            record_video_size={'width': 1080, 'height': 1920}
        )
        page = await context.new_page()
        await page.goto(TOOL_URL, wait_until="networkidle")
        await page.wait_for_timeout(4000)

        await page.mouse.wheel(0, 800)
        await page.wait_for_timeout(3000)
        await page.mouse.wheel(0, -400)
        await page.wait_for_timeout(3000)

        await context.close()
        await browser.close()

def generate_script():
    print("[2/4] Generating script via Claude 3.5 Sonnet...")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Write a 15-second viral Instagram Reel hook script targeting small content creators about this tool: {TOOL_URL}. Keep it under 35 words. Pure voiceover text only."

    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    script_text = res.json()['choices'][0]['message']['content'].strip()
    print(f"Script: {script_text}")
    return script_text

async def generate_voiceover(text):
    print("[3/4] Generating voiceover via Edge-TTS...")
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save("output/voice.mp3")

async def main():
    os.makedirs("output", exist_ok=True)
    await record_screen()
    script = generate_script()
    await generate_voiceover(script)
    print("[4/4] Asset generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
