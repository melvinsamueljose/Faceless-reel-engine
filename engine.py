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

def fetch_past_performance_context():
    """
    Retrieves performance stats from Instagram Graph API or local database context.
    Passes historical insights to Gemini for optimization.
    """
    instagram_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    
    if not instagram_token or not user_id:
        print("[Analytics Warning] Instagram API credentials not set. Using default optimization context.")
        return "Historical Benchmark: Focus on high-converting 2-second pain point hooks."

    try:
        # Fetch last 10 reels metrics via Instagram Insights API
        url = f"https://graph.facebook.com/v19.0/{user_id}/media?fields=id,caption,insights.metric(plays,reach,saved,shares)&access_token={instagram_token}"
        res = requests.get(url, timeout=10)
        data = res.json()
        return f"Past Reels Analytics Data: {str(data)[:2000]}"
    except Exception as e:
        print(f"[Analytics Error] Could not fetch insights: {e}")
        return "Focus on short punchy hooks under 15 seconds."

def generate_storyboard_and_script():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY secret is not set in GitHub Secrets.")

    performance_context = fetch_past_performance_context()

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prompting Gemini 1.5 Pro to leverage performance context for a structured script breakdown
    prompt = f"""
    You are an elite short-form video producer. 
    Analyze this account performance context:
    "{performance_context}"

    Generate a 15-second viral Instagram Reel plan. 
    Return your response strictly in JSON format with two keys:
    1. "voiceover": "The exact full continuous voiceover text string with no stage directions."
    2. "storyboard": "A clear, detailed time-stamped breakdown (0-2s, 2-5s, 5-10s, 10-15s) detailing Voiceover, Actions performed on screen, and Camera/Visual movement."
    """

    models_to_try = [
        "google/gemini-pro-1.5",
        "anthropic/claude-3.5-sonnet",
        "openrouter/auto"
    ]

    for model_slug in models_to_try:
        print(f"Attempting script & storyboard generation with model: {model_slug}...")
        payload = {
            "model": model_slug,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            data = res.json()

            if "choices" in data and len(data["choices"]) > 0:
                import json
                result = json.loads(data["choices"][0]["message"]["content"])
                return result["voiceover"], result["storyboard"]
        except Exception as e:
            print(f"Request failed for model {model_slug}: {e}")

    # Fallback if JSON parsing fails
    fallback_vo = "Stop wasting hours making carousels manually. This AI tool generates high-converting slides in seconds."
    fallback_board = (
        "🎬 0s - 2s (HOOK)\n• Voiceover: Stop wasting hours making carousels manually.\n• Action: Hover over main landing page CTA button.\n\n"
        "🎬 2s - 10s (DEMO)\n• Voiceover: This AI tool generates high-converting slides in seconds.\n• Action: Click CTA, navigate to app, type sample query, and click Generate.\n\n"
        "🎬 10s - 15s (CTA)\n• Voiceover: Try it today for free!\n• Action: Scroll through output templates."
    )
    return fallback_vo, fallback_board

def authorize_via_telegram(initial_vo, storyboard_text):
    print("[Telegram Gate] Sending complete storyboard preview to Telegram...")
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
        "🎬 *NEW REEL STORYBOARD PREVIEW*\n\n"
        f"{storyboard_text}\n\n"
        "----------------------------------\n"
        "🎙️ *Full Spoken Voiceover Script*:\n"
        f"\"{initial_vo}\"\n\n"
        "👉 Tap *Authorize* to render as-is.\n"
        "👉 *Reply to this message* to edit the voiceover script before authorising!"
    )

    res = requests.post(send_url, json={
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    })
    
    if res.status_code != 200:
        print(f"[Telegram Gate Error] Failed to send preview: {res.text}")
        return initial_vo

    current_vo = initial_vo
    offset = None
    start_time = time.time()

    # Poll Telegram updates for 10 minutes
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

                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data")
                        
                        if cb_data == "APPROVED":
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": "Authorized!"})
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": f"🚀 Authorized! Rendering Reel with script:\n\n\"{current_vo}\""})
                            return current_vo
                        
                        elif cb_data == "CANCELLED":
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": "Cancelled."})
                            raise SystemExit("Job manually cancelled by user via Telegram.")

                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        if str(msg["chat"]["id"]) == str(CHAT_ID):
                            current_vo = msg["text"].strip()
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": CHAT_ID,
                                "text": f"✏️ Voiceover script updated to:\n\n\"{current_vo}\"\n\nNow tap *Authorize & Render* on the storyboard message!",
                                "reply_to_message_id": msg["message_id"]
                            })

        except SystemExit:
            raise
        except Exception as e:
            print(f"[Telegram Gate Error] Polling error: {e}")

        time.sleep(2)

    return current_vo

async def generate_voiceover(text, output_path):
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-AriaNeural"]
    for voice in voices:
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return
        except Exception:
            await asyncio.sleep(2)
    raise RuntimeError("All edge-tts voice endpoints failed.")

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_subtitles(audio_path, srt_path):
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
        
        await page.goto(target_url, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        
        for _ in range(3):
            await page.mouse.wheel(0, 250)
            await page.wait_for_timeout(400)

        try:
            cta_button = page.locator("a:has-text('Create Carousel'), button:has-text('Create Carousel'), a[href*='app']").first
            if await cta_button.is_visible():
                await cta_button.hover()
                await page.wait_for_timeout(800)
                await cta_button.click()
                await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[Playwright] CTA fallback: {e}")

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
            print(f"[Playwright] Input fallback: {e}")

        for _ in range(4):
            await page.mouse.wheel(0, 300)
            await page.wait_for_timeout(500)

        await context.close()
        await browser.close()

def assemble_dynamic_reel(raw_video_path, audio_path, srt_path, output_path):
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

async def main():
    os.makedirs("output", exist_ok=True)
    tool_url = os.getenv("TOOL_URL", "https://aicarousels.com")

    # Step 1: Generate script & storyboard with performance feedback
    print("[1/6] Generating storyboard & script via Gemini 1.5 Pro...")
    initial_vo, storyboard = generate_storyboard_and_script()

    # Step 2: Authorize/Edit preview in Telegram
    print("[2/6] Awaiting Telegram approval...")
    final_vo = authorize_via_telegram(initial_vo, storyboard)

    # Step 3: Record UI Interactions
    print("[3/6] Executing dynamic screen recording...")
    await record_interactive_demo(tool_url, "output")
    
    raw_files = [os.path.join("output", f) for f in os.listdir("output") if f.endswith('.webm') or f.endswith('.mp4')]
    if not raw_files:
        raise FileNotFoundError("Playwright failed to capture interactive recording.")
    raw_video = raw_files[0]

    # Step 4: Render Voiceover
    print("[4/6] Rendering TTS voiceover...")
    audio_file = "output/voice.mp3"
    await generate_voiceover(final_vo, audio_file)

    # Step 5: Subtitles via Whisper
    print("[5/6] Generating captions...")
    srt_file = "output/subtitles.srt"
    generate_subtitles(audio_file, srt_file)

    # Step 6: Render Final Reel
    print("[6/6] Assembling final Reel with FFmpeg...")
    final_video = "output/final_reel.mp4"
    assemble_dynamic_reel(raw_video, audio_file, srt_file, final_video)

    print("Pipeline completed! File saved at output/final_reel.mp4")

if __name__ == "__main__":
    asyncio.run(main())
