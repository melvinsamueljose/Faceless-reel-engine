import os
import asyncio
import requests
import edge_tts
from playwright.async_api import async_playwright

def generate_script():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY secret is not set in GitHub Secrets.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "Write a punchy, viral 15-second script for an Instagram Reel promoting an AI tool. "
        "Return ONLY the plain spoken voiceover script text with no stage directions or formatting."
    )

    payload = {
        "model": "anthropic/claude-sonnet-5",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if "choices" not in data:
        print(f"OpenRouter Error Payload: {data}")
        raise KeyError(f"OpenRouter call failed. Check credits or key.")

    return data["choices"][0]["message"]["content"].strip()

async def generate_voiceover(text, output_path):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_path)

async def record_screen(target_url, output_dir):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=output_dir,
            record_video_size={"width": 1080, "height": 1920}
        )
        page = await context.new_page()
        print(f"Navigating to {target_url}...")
        await page.goto(target_url, wait_until="networkidle")
        await page.wait_for_timeout(10000)  # Record 10 seconds of interaction/scrolling
        await context.close()
        await browser.close()

async def main():
    # Force-create output directory immediately
    os.makedirs("output", exist_ok=True)

    tool_url = os.getenv("TOOL_URL", "https://aicarousels.com")

    print("[1/3] Recording screen...")
    await record_screen(tool_url, "output")

    print("[2/3] Generating script via AI...")
    script_text = generate_script()

    print("[3/3] Generating voiceover audio...")
    await generate_voiceover(script_text, "output/voice.mp3")

    print("All assets generated successfully in output/")

if __name__ == "__main__":
    asyncio.run(main())
