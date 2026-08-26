import os
import sys
import json
import re
import asyncio
import requests
from playwright.async_api import async_playwright

def clean_token(token_str):
    token = re.sub(r'[\[\]\'"\s]', '', token_str)
    if "bot" in token:
        token = token.split("bot")[-1]
    return token

def get_ai_script(target_url):
    custom_hook = os.getenv("CUSTOM_HOOK", "").strip()
    custom_voiceover = os.getenv("CUSTOM_VOICEOVER", "").strip()

    # Priority 1: Use direct manual inputs if provided by user
    if custom_hook and custom_voiceover:
        print("[SCRIPT ENGINE] Using manually provided custom Hook and Voiceover.")
        return {
            "hook": custom_hook,
            "voiceover": custom_voiceover
        }

    # Priority 2: Use AI to generate based on custom prompt instructions
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    ai_instructions = os.getenv("AI_PROMPT_INSTRUCTIONS", "Create an engaging 10-second Reel script.").strip()
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not api_key:
        print("[AI SCRIPT] No OPENROUTER_API_KEY found, using standard fallback.")
        return {
            "hook": custom_hook if custom_hook else "INSANE AI TOOL FOR CREATORS!",
            "voiceover": custom_voiceover if custom_voiceover else f"Check out {domain}. It automates your workflow in seconds."
        }

    prompt = (
        f"{ai_instructions}\n"
        f"Target URL: {target_url}\n"
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
                "model": "google/gemini-2.0-flash-001",
                "messages": [{"role": "user", "content": prompt}]
            }),
            timeout=15
        )
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            raw_text = data['choices'][0]['message']['content'].strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            res_json = json.loads(raw_text)
            
            # Allow manual override for individual fields if supplied
            if custom_hook: res_json["hook"] = custom_hook
            if custom_voiceover: res_json["voiceover"] = custom_voiceover
            return res_json
        else:
            raise KeyError(f"OpenRouter response missing choices: {data}")
    except Exception as e:
        print(f"[AI SCRIPT ERROR] {e}. Using fallback values.")
        return {
            "hook": custom_hook if custom_hook else "STOP MAKING CAROUSELS MANUALLY!",
            "voiceover": custom_voiceover if custom_voiceover else f"If you are building digital content, {domain} automates your workflow instantly."
        }

async def capture_screen(target_url, output_path="raw_desktop.webm"):
    action = os.getenv("CAPTURE_ACTION", "click_try").strip().lower()
    print(f"[RECORDER] Launching desktop recorder for {target_url} (Action: {action})...")
    
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
            
            if action == "click_try":
                btn = page.locator("a:has-text('Try'), button:has-text('Create'), a:has-text('Get Started'), a.btn").first
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(4)
                else:
                    await page.mouse.wheel(0, 600)
                    await asyncio.sleep(4)
            elif action == "scroll":
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(2)
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(2)
            elif action == "full_page":
                for _ in range(3):
                    await page.mouse.wheel(0, 400)
                    await asyncio.sleep(1.5)
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
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_token = clean_token(raw_token)
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))

    caption = (
        f"📹 *Raw 1920x1080 Desktop Footage Captured*\n\n"
        f"📌 *Hook:* {script_data['hook']}\n"
        f"🎙️ *Voiceover:* {script_data['voiceover']}\n\n"
        f"Ready for Stage 2 HyperFrames rendering!"
    )

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/sendVideo"
    with open(video_path, "rb") as vf:
        requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
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
