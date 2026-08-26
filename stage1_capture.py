import os
import sys
import json
import asyncio
import requests
from playwright.async_api import async_playwright

def get_ai_script(target_url):
    api_key = os.getenv("OPENROUTER_API_KEY")
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not api_key:
        print("[AI SCRIPT] No OPENROUTER_API_KEY found, using standard fallback script.")
        return {
            "hook": "STOP MAKING CAROUSELS MANUALLY!",
            "voiceover": f"Check out {domain}. This AI tool designs high converting carousels automatically in seconds."
        }

    prompt = (
        f"Create an engaging 10-second Reel script for web tool: {target_url}.\n"
        f"Return ONLY a JSON object with keys:\n"
        f"1. 'hook': A short 4-6 word punchy uppercase text overlay.\n"
        f"2. 'voiceover': A concise 25-30 word script explaining what the tool does."
    )

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": prompt}]
            }),
            timeout=15
        )
        data = response.json()
        raw_text = data['choices'][0]['message']['content'].strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        print(f"[AI SCRIPT ERROR] {e}. Using fallback values.")
        return {
            "hook": "INSANE AI TOOL FOR CREATORS!",
            "voiceover": f"If you are building digital content, {domain} automates your workflow instantly."
        }

async def capture_screen(target_url, output_path="raw_desktop.webm"):
    print(f"[RECORDER] Launching desktop Firefox context for {target_url}...")
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir="temp_raw",
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            btn = page.locator("a:has-text('Try'), button:has-text('Create'), a.btn").first
            if await btn.is_visible():
                await btn.click()
                await asyncio.sleep(4)
            else:
                await page.mouse.wheel(0, 600)
                await asyncio.sleep(4)
        except Exception as e:
            print(f"[CAPTURE WARNING] {e}")
        finally:
            await context.close()
            await browser.close()

    raw_dir = "temp_raw"
    videos = [os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.endswith(".webm")]
    if videos:
        os.rename(max(videos, key=os.path.getctime), output_path)
        print(f"[RECORDER] Raw desktop footage saved: {output_path}")

def notify_telegram(video_path, script_data):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(" '\"[]")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip(" '\"[]")

    caption = (
        f"📹 *Raw 1920x1080 Desktop Footage Captured*\n\n"
        f"📌 *Hook:* {script_data['hook']}\n"
        f"🎙️ *Voiceover:* {script_data['voiceover']}\n\n"
        f"Ready for HyperFrames rendering!"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    with open(video_path, "rb") as vf:
        requests.post(
            url,
            data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown"
            },
            files={"video": vf}
        )

async def main():
    url = os.getenv("TARGET_URL", "[https://aicarousels.com](https://aicarousels.com)")
    script = get_ai_script(url)
    
    with open("script.json", "w") as f:
        json.dump(script, f)

    await capture_screen(url)
    notify_telegram("raw_desktop.webm", script)

if __name__ == "__main__":
    asyncio.run(main())
