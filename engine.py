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
        "Return ONLY the plain spoken voiceover script text with no stage directions, quotes, or formatting."
    )

    # List models in order of priority: Sonnet 5 -> Claude 3.5 Sonnet -> OpenRouter Auto
    models_to_try = [
        "anthropic/claude-sonnet-5",
        "anthropic/claude-3.5-sonnet",
        "openrouter/auto"
    ]

    for model_slug in models_to_try:
        print(f"Attempting script generation with model: {model_slug}...")
        payload = {
            "model": model_slug,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            data = res.json()

            if "choices" in data and len(data["choices"]) > 0:
                script_text = data["choices"][0]["message"]["content"].strip()
                print(f"Successfully generated script using {model_slug}!")
                return script_text
            else:
                print(f"Model {model_slug} returned non-standard payload: {data}")
        except Exception as e:
            print(f"Request failed for model {model_slug}: {e}")

    raise KeyError("All OpenRouter model endpoints failed. Please check your API key, credits, or connectivity.")

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
        await page.wait_for_timeout(10000)  # Record 10 seconds of interaction
        await context.close()
        await browser.close()

async def main():
    # 1. Guarantee output folder exists at startup
    os.makedirs("output", exist_ok=True)

    tool_url = os.getenv("TOOL_URL", "https://aicarousels.com")

    print("[1/3] Recording target website screen...")
    await record_screen(tool_url, "output")

    print("[2/3] Generating script via Anthropic Claude...")
    script_text = generate_script()
    print(f"Generated Script:\n\"{script_text}\"")

    print("[3/3] Rendering voiceover audio...")
    await generate_voiceover(script_text, "output/voice.mp3")

    print("Pipeline completed cleanly! All assets stored in output/")

if __name__ == "__main__":
    asyncio.run(main())
