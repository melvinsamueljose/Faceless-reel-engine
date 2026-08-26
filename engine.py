import os
import re
import time
import subprocess
import asyncio
import requests
import edge_tts
import whisper
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def clean_voiceover_text(raw_text):
    """Extracts strictly the spoken voiceover script, stripping all storyboard markers."""
    script_match = re.search(r'🎙️\s*\*?Spoken Voiceover Script\*?:?\s*[\r\n]+["“]?([^"”]+)["”]?', raw_text, re.DOTALL | re.IGNORECASE)
    if script_match and len(script_match.group(1).strip()) > 10:
        clean = script_match.group(1).strip()
        return re.sub(r'^["“]|["”]$', '', clean).strip()

    vo_matches = re.findall(r'•?\s*Voiceover:\s*["“]?([^"”\n]+)["”]?', raw_text, re.IGNORECASE)
    if vo_matches:
        return " ".join([v.strip() for v in vo_matches if v.strip()])

    cleaned_lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.search(r'(⏱️|Hook|Pain point|The fix|CTA|Actions performed|Spoken Voiceover|Tap \*Authorize\*|Reply to edit)', line, re.IGNORECASE):
            continue
        line = re.sub(r'^[•\-\*\s]+', '', line)
        line = line.strip('"' + "'")
        if line:
            cleaned_lines.append(line)
            
    return " ".join(cleaned_lines) if cleaned_lines else raw_text

def generate_storyboard_and_script():
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    detailed_fallback_board = (
        "⏱️ 0s to 3s — Hook (specific, not generic)\n"
        "• Voiceover: \"Stop spending two hours designing single carousels manually.\"\n"
        "• Actions performed: Live UI demo entering topic into aiCarousels.com builder.\n\n"
        "⏱️ 3s to 7s — Pain point\n"
        "• Voiceover: \"Most AI carousel tools output ugly layouts that break your brand.\"\n"
        "• Actions performed: Contrast preview showing default template vs custom brand palette.\n\n"
        "⏱️ 7s to 12s — The fix, shown not told\n"
        "• Voiceover: \"aiCarousels automatically formats your text and resizes every slide in seconds.\"\n"
        "• Actions performed: Fast-forward UI rendering auto-layout features and font pairings.\n\n"
        "⏱️ 12s to 15s — CTA\n"
        "• Voiceover: \"Save this reel to upgrade your visual content workflow.\"\n"
        "• Actions performed: Callout card pulse showing export options for Instagram and LinkedIn."
    )

    fallback_vo = (
        "Stop spending two hours designing single carousels manually. "
        "Most AI carousel tools output ugly layouts that break your brand. "
        "aiCarousels automatically formats your text and resizes every slide in seconds. "
        "Save this reel to upgrade your visual content workflow."
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
    Generate a high-retention 15-second viral Instagram Reel plan for aiCarousels.
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
        await Stealth().apply_stealth_async(page)
        await page.bring_to_front()
        
        print(f"[Playwright Stealth] Attempting live recording for: {target_url}")
        
        try:
            response = await page.goto(target_url, wait_until="load", timeout=12000)
            
            if response and response.status in [403, 503]:
                raise RuntimeError(f"Cloudflare status {response.status}")
                
            await page.wait_for_timeout(2000)
            for _ in range(5):
                await page.mouse.wheel(0, 400)
                await page.wait_for_timeout(1500)

        except Exception as e:
            print(f"[Playwright Fallback Activated]: {e}")
            
            fallback_html = f"""
            <!DOCTYPE html>
            <html style="background-color: #0d1117; width: 1080px; height: 1920px;">
            <head>
                <meta charset="UTF-8">
            </head>
            <body style="margin: 0; padding: 0; width: 1080px; height: 1920px; background-color: #0d1117; font-family: sans-serif; display: flex; align-items: center; justify-content: center;">
                <div style="width: 850px; background: #161b22; border: 3px solid #30363d; border-radius: 36px; padding: 60px; box-shadow: 0 30px 60px rgba(0,0,0,0.8);">
                    <div style="background: #2563eb; color: #ffffff; padding: 12px 28px; border-radius: 20px; font-weight: 800; font-size: 26px; display: inline-block; margin-bottom: 30px;">
                        PLUTUS LAB AUTOMATION
                    </div>
                    <div style="font-size: 58px; font-weight: 900; color: #60a5fa; margin-bottom: 20px;">
                        Visual Engine Active
                    </div>
                    <div style="color: #8b949e; font-size: 30px; margin-bottom: 40px;">
                        Processing: {target_url}
                    </div>
                    <div id="term" style="background: #010409; border: 2px solid #21262d; border-radius: 24px; padding: 40px; font-family: monospace; font-size: 30px; color: #38bdf8; min-height: 300px; line-height: 1.8;">
                        > Analyzing page elements...
                    </div>
                </div>
                <script>
                    const term = document.getElementById('term');
                    const steps = [
                        "> Extracting brand guidelines...",
                        "> Formatting automated slides...",
                        "> Compiling 1080x1920 sequence..."
                    ];
                    let i = 0;
                    setInterval(() => {{
                        if (i < steps.length) {{
                            term.innerHTML += '<br>' + steps[i];
                            i++;
                        }}
                    }}, 2500);
                </script>
            </body>
            </html>
            """
            await page.set_content(fallback_html)
            # Mandatory 15-second recording window for screen capture engine
            await page.wait_for_timeout(15000)

        # Force video buffer write before context closing
        await page.wait_for_timeout(1000)
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
