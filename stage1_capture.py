import os
import sys
import json
import re
import math
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

    if custom_hook and custom_voiceover:
        return {"hook": custom_hook, "voiceover": custom_voiceover}

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    ai_instructions = os.getenv("AI_PROMPT_INSTRUCTIONS", "Create a high-converting 10-second Reel script.").strip()
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not api_key:
        return {
            "hook": custom_hook if custom_hook else "STOP CREATING CAROUSELS MANUALLY!",
            "voiceover": custom_voiceover if custom_voiceover else f"Check out {domain}. Generate viral social media carousels in seconds using AI."
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
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({"model": "google/gemini-2.0-flash-001", "messages": [{"role": "user", "content": prompt}]}),
            timeout=15
        )
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            raw_text = data['choices'][0]['message']['content'].strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            res_json = json.loads(raw_text)
            if custom_hook: res_json["hook"] = custom_hook
            if custom_voiceover: res_json["voiceover"] = custom_voiceover
            return res_json
        else:
            raise KeyError(f"OpenRouter missing choices: {data}")
    except Exception:
        return {
            "hook": custom_hook if custom_hook else "CREATE CAROUSELS 10X FASTER!",
            "voiceover": custom_voiceover if custom_voiceover else f"If you build content, {domain} automates your design workflow instantly."
        }

async def inject_visual_cursor(page):
    cursor_script = """
    () => {
        const cursor = document.createElement('div');
        cursor.id = 'playwright-visual-cursor';
        cursor.style.position = 'fixed';
        cursor.style.top = '0px';
        cursor.style.left = '0px';
        cursor.style.width = '20px';
        cursor.style.height = '20px';
        cursor.style.border = '2px solid white';
        cursor.style.backgroundColor = 'rgba(255, 69, 0, 0.8)';
        cursor.style.borderRadius = '50%';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '99999999';
        cursor.style.transition = 'transform 0.15s ease, background-color 0.15s ease';
        cursor.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
        document.body.appendChild(cursor);

        window.addEventListener('mousemove', e => {
            cursor.style.left = e.clientX - 10 + 'px';
            cursor.style.top = e.clientY - 10 + 'px';
        });
        window.addEventListener('mousedown', () => {
            cursor.style.transform = 'scale(0.7)';
            cursor.style.backgroundColor = 'rgba(0, 255, 150, 0.9)';
        });
        window.addEventListener('mouseup', () => {
            cursor.style.transform = 'scale(1)';
            cursor.style.backgroundColor = 'rgba(255, 69, 0, 0.8)';
        });
    }
    """
    await page.evaluate(cursor_script)

async def human_move_mouse(page, start_x, start_y, end_x, end_y, steps=35):
    """Generates keyframed smooth mouse movement using cubic bezier easing."""
    for i in range(1, steps + 1):
        t = i / steps
        # Ease-in-out quadratic curve math
        ease_t = 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2
        
        curr_x = start_x + (end_x - start_x) * ease_t
        curr_y = start_y + (end_y - start_y) * ease_t
        
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(0.012)  # ~60fps smooth interpolation

async def human_scroll(page, scroll_amount, steps=25):
    """Keyframed scroll prevent sharp jumps."""
    per_step = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, per_step)
        await asyncio.sleep(0.02)

async def capture_screen(target_url, output_path="raw_desktop.webm"):
    print(f"[RECORDER] Launching precision recorder for {target_url}...")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir="temp_raw",
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=60000)
            await inject_visual_cursor(page)
            
            # Start initial mouse position at top-left off-center
            curr_x, curr_y = 200, 200
            await page.mouse.move(curr_x, curr_y)
            await asyncio.sleep(1.0)

            # Smoothly scroll header section
            await human_scroll(page, 300, steps=20)
            await asyncio.sleep(0.8)

            # Locate primary call-to-action button dynamically
            btn = page.locator("a:has-text('Try'), button:has-text('Create'), a:has-text('Get Started'), a.btn").first
            
            if await btn.is_visible():
                box = await btn.bounding_box()
                if box:
                    target_x = box["x"] + box["width"] / 2
                    target_y = box["y"] + box["height"] / 2
                    
                    # Keyframe smooth move to button
                    await human_move_mouse(page, curr_x, curr_y, target_x, target_y, steps=40)
                    await asyncio.sleep(0.4) # Hover pause
                    
                    # Click with natural hold delay
                    await page.mouse.down()
                    await asyncio.sleep(0.12)
                    await page.mouse.up()
                    
                    await asyncio.sleep(3.0)
            else:
                # Fallback multi-stage scroll if no primary button found
                await human_scroll(page, 500, steps=30)
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
        print(f"[RECORDER] Smooth desktop footage saved: {output_path}")

def notify_telegram(video_path, script_data):
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_token = clean_token(raw_token)
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))

    caption = (
        f"📹 *Precision Smooth Desktop Capture Complete*\n\n"
        f"📌 *Hook:* {script_data['hook']}\n"
        f"🎙️ *Voiceover:* {script_data['voiceover']}\n\n"
        f"Ready for Stage 2 render!"
    )

    # Clean string construction without f-string URL interpolation
    base_url = "https://api.telegram.org/bot" + str(bot_token) + "/sendVideo"
    
    with open(video_path, "rb") as vf:
        requests.post(
            base_url,
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
