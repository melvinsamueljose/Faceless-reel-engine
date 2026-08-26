import os
import time
import subprocess
import asyncio
import requests
import edge_tts
import whisper
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
        "You are an elite short-form video copywriter. Write a fast-paced, viral 15-second Instagram Reel script "
        "demonstrating an AI tool in action. Start with a massive hook in sentence 1. "
        "Focus on how fast the user can generate carousels. "
        "Return ONLY the plain spoken voiceover script string with zero stage directions, quotes, or formatting."
    )

    models_to_try = [
        "anthropic/claude-sonnet-5",
        "anthropic/claude-3.5-sonnet",
        "openrouter/auto"
    ]

    for model_slug in models_to_try:
        print(f"Attempting script generation with model: {model_slug}...")
        payload = {
            "model": model_slug,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150
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

    raise KeyError("All OpenRouter model endpoints failed.")

def authorize_or_edit_via_telegram(initial_script):
    """Sends script to Telegram, waits for user to edit or authorize via inline buttons."""
    print("[Telegram Gate] Sending draft script to Telegram for authorization...")
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Authorize & Render", "callback_data": "APPROVED"},
                {"text": "❌ Cancel Job", "callback_data": "CANCELLED"}
            ]
        ]
    }
    
    message_text = (
        "📝 *Draft Script Generated*\n\n"
        f"\"{initial_script}\"\n\n"
        "👉 Tap *Authorize* to render as-is.\n"
        "👉 *Reply to this message* with your custom text to edit the script, then tap Authorize!"
    )

    res = requests.post(send_url, json={
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    })
    
    if res.status_code != 200:
        print(f"[Telegram Gate Error] Failed to send authorization message: {res.text}")
        return initial_script

    sent_message_id = res.json()["result"]["message_id"]
    print(f"[Telegram Gate] Message ID {sent_message_id} sent. Waiting up to 600s for user input...")

    current_script = initial_script
    offset = None
    start_time = time.time()

    # Poll Telegram updates for up to 10 minutes
    while time.time() - start_time < 600:
        updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"timeout": 10}
        if offset:
            params["offset"] = offset

        try:
            u_res = requests.get(updates_url, params=params, timeout=15)
            data = u_res.json()

            if "result" in data:
                for update in data["result"]:
                    offset = update["update_id"] + 1

                    # Check for Inline Button Clicks
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data")
                        
                        if cb_data == "APPROVED":
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": "Authorized!"})
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": f"🚀 Script Authorized! Rendering Reel with:\n\n\"{current_script}\""})
                            return current_script
                        
                        elif cb_data == "CANCELLED":
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": "Job Cancelled."})
                            raise SystemExit("Job manually cancelled by user via Telegram.")

                    # Check for Reply Text Messages to edit script
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        if str(msg["chat"]["id"]) == str(CHAT_ID):
                            current_script = msg["text"].strip()
                            print(f"[Telegram Gate] Script updated by user reply: {current_script}")
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": CHAT_ID,
                                "text": f"✏️ Script updated to:\n\n\"{current_script}\"\n\nNow tap *Authorize & Render* on the main prompt message!",
                                "reply_to_message_id": msg["message_id"]
                            })

        except SystemExit:
            raise
        except Exception as e:
            print(f"[Telegram Gate Error] Polling error: {e}")

        time.sleep(2)

    print("[Telegram Gate] Timeout reached (10m). Proceeding with current script draft...")
    return current_script

async def generate_voiceover(text, output_path):
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-AriaNeural"]
    for voice in voices:
        print(f"Trying edge-tts voice: {voice}...")
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            print(f"Voiceover successfully rendered with {voice}!")
            return
        except Exception as e:
            print(f"Voice {voice} failed: {e}. Retrying...")
            await asyncio.sleep(2)
            
    raise RuntimeError("All edge-tts voice endpoints failed.")

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_subtitles(audio_path, srt_path):
    print("[Whisper] Transcribing audio for dynamic captions...")
    model = whisper.load_model("tiny")
    result = model.transcribe(audio_path)
    
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(result["segments"], start=1):
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            text = segment["text"].strip().upper()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

async def record_interactive_demo(target_url, output_dir):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=output_dir,
            record_video_size={"width": 1080, "height": 1920}
        )
        page = await context.new_page()
        
        print(f"[Playwright] Navigating to {target_url}...")
        await page.goto(target_url, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        
        for _ in range(3):
            await page.mouse.wheel(0, 250)
            await page.wait_for_timeout(400)

        print("[Playwright] Locating and clicking 'Create Carousel' button...")
        try:
            cta_button = page.locator("a:has-text('Create Carousel'), button:has-text('Create Carousel'), a[href*='app']").first
            if await cta_button.is_visible():
                await cta_button.hover()
                await page.wait_for_timeout(800)
                await cta_button.click()
                print("[Playwright] Clicked CTA. Waiting for app page to load...")
                await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[Playwright] Navigation click fallback: {e}")

        print("[Playwright] Simulating active usage on app screen...")
        try:
            text_input = page.locator("textarea, input[type='text']").first
            if await text_input.is_visible():
                await text_input.click()
                await text_input.type("5 Secret AI Tools for 2026", delay=80)
                await page.wait_for_timeout(1000)

            gen_button = page.locator("button:has-text('Generate'), button:has-text('Next'), button[type='submit']").first
            if await gen_button.is_visible():
                await gen_button.hover()
                await page.wait_for_timeout(600)
                await gen_button.click()
                await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"[Playwright] App interaction fallback: {e}")

        for _ in range(4):
            await page.mouse.wheel(0, 300)
            await page.wait_for_timeout(500)

        await context.close()
        await browser.close()

def assemble_dynamic_reel(raw_video_path, audio_path, srt_path, output_path):
    print("[FFmpeg] Applying keyframed zoom animation and burning dynamic captions...")
    
    filter_complex = (
        "zoompan=z='min(zoom+0.0012,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=450:s=1080x1920,"
        f"subtitles={srt_path}:force_style='FontSize=22,FontName=Impact,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2'"
    )

    command = [
        "ffmpeg", "-y",
        "-i", raw_video_path,
        "-i", audio_path,
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    
    subprocess.run(command, check=True)
    print(f"[FFmpeg] Dynamic Reel compiled cleanly: {output_path}")

async def main():
    os.makedirs("output", exist_ok=True)
    tool_url = os.getenv("TOOL_URL", "https://aicarousels.com")

    # Step 1: Generate initial script draft
    print("[1/6] Generating viral script draft via Claude Sonnet 5...")
    initial_script = generate_script()
    print(f"Generated Script Draft:\n\"{initial_script}\"")

    # Step 2: Send script to Telegram & wait for user authorization/edits
    print("[2/6] Waiting for Telegram authorization...")
    final_script = authorize_or_edit_via_telegram(initial_script)
    print(f"Final Authorized Script:\n\"{final_script}\"")

    # Step 3: Record Interactive Web Demo
    print("[3/6] Recording multi-page interactive tool demo...")
    await record_interactive_demo(tool_url, "output")

    raw_files = [os.path.join("output", f) for f in os.listdir("output") if f.endswith('.webm') or f.endswith('.mp4')]
    if not raw_files:
        raise FileNotFoundError("Playwright failed to capture interactive recording.")
    raw_video = raw_files[0]

    # Step 4: Voiceover Generation using authorized script
    print("[4/6] Rendering voiceover via edge-tts...")
    audio_file = "output/voice.mp3"
    await generate_voiceover(final_script, audio_file)

    # Step 5: Subtitle Generation via Whisper
    print("[5/6] Transcribing audio with OpenAI Whisper...")
    srt_file = "output/subtitles.srt"
    generate_subtitles(audio_file, srt_file)

    # Step 6: Render Final Video with FFmpeg
    print("[6/6] Assembling final Reel with FFmpeg keyframed animations...")
    final_video = "output/final_reel.mp4"
    assemble_dynamic_reel(raw_video, audio_file, srt_file, final_video)

    print("Pipeline finished successfully! Output stored at output/final_reel.mp4")

if __name__ == "__main__":
    asyncio.run(main())
