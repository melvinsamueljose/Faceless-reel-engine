import os
import subprocess
import asyncio
import requests
import edge_tts
import whisper
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
    """Executes authentic multi-page navigation, clicks, scrolling, and typing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=output_dir,
            record_video_size={"width": 1080, "height": 1920}
        )
        page = await context.new_page()
        
        # 1. Open Landing Page & Initial Scroll
        print(f"[Playwright] Navigating to {target_url}...")
        await page.goto(target_url, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        
        for _ in range(3):
            await page.mouse.wheel(0, 250)
            await page.wait_for_timeout(400)

        # 2. Click "Create Carousel" and Navigate to App Page
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

        # 3. Simulate User Interaction on App/Generator Screen
        print("[Playwright] Simulating active usage on app screen...")
        try:
            # Find input field, click, and type sample topic
            text_input = page.locator("textarea, input[type='text']").first
            if await text_input.is_visible():
                await text_input.click()
                await text_input.type("5 Secret AI Tools for 2026", delay=80)
                await page.wait_for_timeout(1000)

            # Look for Generate / Submit button
            gen_button = page.locator("button:has-text('Generate'), button:has-text('Next'), button[type='submit']").first
            if await gen_button.is_visible():
                await gen_button.hover()
                await page.wait_for_timeout(600)
                await gen_button.click()
                await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"[Playwright] App interaction fallback: {e}")

        # 4. Final page scroll showcase
        for _ in range(4):
            await page.mouse.wheel(0, 300)
            await page.wait_for_timeout(500)

        await context.close()
        await browser.close()

def assemble_dynamic_reel(raw_video_path, audio_path, srt_path, output_path):
    print("[FFmpeg] Applying keyframed zoom/pan animation and burning dynamic captions...")
    
    # Dynamic continuous zoompan combined with bold yellow bottom captions
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

    print("[1/5] Recording multi-page interactive tool demo...")
    await record_interactive_demo(tool_url, "output")

    raw_files = [os.path.join("output", f) for f in os.listdir("output") if f.endswith('.webm') or f.endswith('.mp4')]
    if not raw_files:
        raise FileNotFoundError("Playwright failed to capture interactive recording.")
    raw_video = raw_files[0]

    print("[2/5] Generating viral script via Claude Sonnet 5...")
    script_text = generate_script()
    print(f"Generated Script:\n\"{script_text}\"")

    print("[3/5] Rendering voiceover via edge-tts...")
    audio_file = "output/voice.mp3"
    await generate_voiceover(script_text, audio_file)

    print("[4/5] Transcribing audio with OpenAI Whisper...")
    srt_file = "output/subtitles.srt"
    generate_subtitles(audio_file, srt_file)

    print("[5/5] Assembling final Reel with FFmpeg keyframed animations...")
    final_video = "output/final_reel.mp4"
    assemble_dynamic_reel(raw_video, audio_file, srt_file, final_video)

    print("Pipeline finished successfully! Output stored at output/final_reel.mp4")

if __name__ == "__main__":
    asyncio.run(main())
