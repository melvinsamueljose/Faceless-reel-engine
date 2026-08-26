import os
import re
import time
import subprocess
import asyncio
import requests
import edge_tts
import whisper
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def clean_voiceover_text(raw_text):
    """Strips scene labels, VO headers, and timestamps from user input."""
    vo_matches = re.findall(r'VO:\s*["“]([^"”]+)["”]', raw_text, re.IGNORECASE)
    if vo_matches:
        return " ".join(vo_matches)

    cleaned_lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if re.match(r'^(Action|Camera|Visual|Scene|\d+-\d+s|---)', line, re.IGNORECASE):
            continue
        line = re.sub(r'^VO:\s*', '', line, flags=re.IGNORECASE)
        line = line.strip('"' + "'")
        if line:
            cleaned_lines.append(line)
            
    return " ".join(cleaned_lines)

def generate_storyboard_and_script():
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    detailed_fallback_board = (
        "⏱️ 0s to 3s — Hook (specific, not generic)\n"
        "• Voiceover: \"I tested 47 AI hook-generators. Most of them write the exact same opening line.\"\n"
        "• Actions performed: Dynamic UI loading with real-time hook analysis counters.\n\n"
        "⏱️ 3s to 7s — Pain point\n"
        "• Voiceover: \"That's why your reel gets 12 views while a stolen version gets 200k.\"\n"
        "• Actions performed: Comparison analytics dashboard showing low vs viral reach.\n\n"
        "⏱️ 7s to 12s — The fix, shown not told\n"
        "• Voiceover: \"Here's the one prompt that actually forces a unique angle.\"\n"
        "• Actions performed: Live terminal typing sequence rendering high-converting prompt.\n\n"
        "⏱️ 12s to 15s — CTA\n"
        "• Voiceover: \"Save this before your next script.\"\n"
        "• Actions performed: Callout card pulse with link-in-bio prompt overlay."
    )

    fallback_vo = (
        "I tested 47 AI hook-generators. Most of them write the exact same opening line. "
        "That's why your reel gets 12 views while a stolen version gets 200k. "
        "Here's the one prompt that actually forces a unique angle. "
        "Save this before your next script."
    )

    if not api_key:
        return fallback_vo, detailed_fallback_board

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    You are an elite short-form video producer.
    Generate a high-retention 15-second viral Instagram Reel plan.
    Return response strictly in JSON format with two keys:
    1. "voiceover": "{fallback_vo}"
    2. "storyboard": "{detailed_fallback_board}"
    """

    payload = {
        "model": "anthropic/claude-3.5-sonnet",
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
        print(f"[Script Gen Fallback]: {e}")

    return fallback_vo, detailed_fallback_board

def authorize_via_telegram(initial_vo, storyboard_text):
    print("[Telegram Gate] Sending preview to Telegram...")
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
        "🎙️ *Spoken Voiceover Script*:\n"
        f"\"{initial_vo}\"\n\n"
        "👉 Tap *Authorize* to render.\n"
        "👉 *Reply to edit text* first!"
    )

    requests.post(send_url, json={
        "chat_id": CHAT_ID,
        "text": message_text,
        "reply_markup": keyboard
    })

    current_vo = initial_vo
    offset = None
    start_time = time.time()

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
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": f"🚀 Authorized! Rendering Reel..."})
                            return current_vo
                        
                        elif cb_data == "CANCELLED":
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": "Cancelled."})
                            raise SystemExit("Job manually cancelled by user.")

                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        if str(msg["chat"]["id"]) == str(CHAT_ID):
                            raw_input = msg["text"].strip()
                            current_vo = clean_voiceover_text(raw_input)
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": CHAT_ID,
                                "text": f"✏️ Clean Voiceover script updated to:\n\n\"{current_vo}\"\n\nTap *Authorize & Render* to proceed!",
                                "reply_to_message_id": msg["message_id"]
                            })

        except SystemExit:
            raise
        except Exception as e:
            print(f"[Telegram Polling Error]: {e}")

        time.sleep(2)

    return current_vo

async def generate_voiceover(text, output_path):
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural"]
    for voice in voices:
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return
        except Exception:
            await asyncio.sleep(2)
    raise RuntimeError("Edge-TTS voice rendering failed.")

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_subtitles(audio_path, srt_path):
    """Generates short, 2-3 word captions with strict line breaking."""
    print("[Whisper] Extracting word-level timestamps...")
    model = whisper.load_model("tiny")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    words = []
    for segment in result["segments"]:
        for word_info in segment.get("words", []):
            words.append(word_info)

    with open(srt_path, "w", encoding="utf-8") as f:
        caption_idx = 1
        chunk_size = 3
        
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            if not chunk:
                continue
            
            start_time = format_timestamp(chunk[0]["start"])
            end_time = format_timestamp(chunk[-1]["end"])
            text = " ".join([w["word"].strip().upper() for w in chunk])
            
            f.write(f"{caption_idx}\n{start_time} --> {end_time}\n{text}\n\n")
            caption_idx += 1

async def record_interactive_demo(target_url, output_dir):
    """Uses stealth patches to attempt live site capture, falling back gracefully if blocked."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            record_video_dir=output_dir,
            record_video_size={"width": 1080, "height": 1920}
        )
        
        page = await context.new_page()
        await stealth_async(page)
        
        print(f"[Playwright Stealth] Attempting live recording for: {target_url}")
        
        try:
            response = await page.goto(target_url, wait_until="networkidle", timeout=20000)
            
            # Check if Cloudflare block page was returned
            if response and response.status in [403, 503]:
                raise RuntimeError(f"Cloudflare returned status code {response.status}")
                
            await page.wait_for_timeout(2000)
            
            # Interact with live page
            for _ in range(4):
                await page.mouse.wheel(0, 300)
                await page.wait_for_timeout(600)

        except Exception as e:
            print(f"[Playwright Stealth Warning]: {e}. Fallback UI activated...")
            
            dynamic_ui_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    * {{ box-sizing: border-box; }}
                    body {{
                        margin: 0; padding: 0;
                        width: 1080px; height: 1920px;
                        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #0f172a 100%);
                        color: #f8fafc; font-family: sans-serif;
                        display: flex; flex-direction: column;
                        align-items: center; justify-content: center;
                    }}
                    .card {{
                        width: 880px; background: rgba(30, 41, 59, 0.7);
                        border: 2px solid rgba(255, 255, 255, 0.1);
                        border-radius: 24px; padding: 48px;
                    }}
                    .title {{ font-size: 42px; font-weight: 800; color: #60a5fa; }}
                    .console {{
                        background: #020617; border-radius: 16px;
                        padding: 28px; font-family: monospace; font-size: 24px;
                        color: #38bdf8; margin-top: 32px; min-height: 180px;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div style="background:#3b82f6; display:inline-block; padding:8px 18px; border-radius:20px; font-weight:bold;">PLUTUS LAB AI</div>
                    <div class="title">Hook Engine Analysis</div>
                    <p style="color:#94a3b8; font-size:20px;">Target: {target_url}</p>
                    <div class="console" id="terminal">> Initializing workflow automation...</div>
                </div>
                <script>
                    const term = document.getElementById('terminal');
                    const logs = ["> Processing hook variations...", "> Testing conversion rates...", "> Finalizing video assembly..."];
                    let i = 0;
                    setInterval(() => {{ if(i < logs.length) {{ term.innerHTML += '<br>' + logs[i]; i++; }} }}, 2000);
                </script>
            </body>
            </html>
            """
            await page.set_content(dynamic_ui_html)
            await page.wait_for_timeout(10000)

        await page.close()
        await context.close()
        await browser.close()

def assemble_dynamic_reel(raw_video_path, audio_path, srt_path, output_path):
    print("[FFmpeg] Burning styled captions and applying zoompan...")
    
    subtitle_style = (
        "FontName=DejaVu Sans,"
        "FontSize=12,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "BackColour=&H80000000,"
        "BorderStyle=3,"
        "Outline=1,"
        "Shadow=0,"
        "Alignment=2,"
        "MarginV=180"
    )

    filter_complex = (
        "zoompan=z='min(zoom+0.001,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=450:s=1080x1920,"
        f"subtitles={srt_path}:force_style='{subtitle_style}'"
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
    print(f"[FFmpeg] Compiled successfully: {output_path}")

async def main():
    os.makedirs("output", exist_ok=True)
    tool_url = os.getenv("TOOL_URL", "https://aicarousels.com")

    print("[1/6] Generating script & storyboard breakdown...")
    initial_vo, storyboard = generate_storyboard_and_script()

    print("[2/6] Waiting for Telegram approval...")
    final_vo = authorize_via_telegram(initial_vo, storyboard)

    print("[3/6] Recording interactive web UI...")
    await record_interactive_demo(tool_url, "output")
    
    raw_files = [os.path.join("output", f) for f in os.listdir("output") if f.endswith('.webm') or f.endswith('.mp4')]
    if not raw_files:
        raise FileNotFoundError("Playwright failed to produce output recording.")
    raw_video = raw_files[0]

    print("[4/6] Rendering TTS audio...")
    audio_file = "output/voice.mp3"
    await generate_voiceover(final_vo, audio_file)

    print("[5/6] Generating word-level subtitles...")
    srt_file = "output/subtitles.srt"
    generate_subtitles(audio_file, srt_file)

    print("[6/6] Rendering video assembly...")
    final_video = "output/final_reel.mp4"
    assemble_dynamic_reel(raw_video, audio_file, srt_file, final_video)

    print("Pipeline run finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
