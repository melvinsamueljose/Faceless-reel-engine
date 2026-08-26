import os
import sys
import json
import asyncio
import math
import requests
from PIL import Image, ImageDraw, ImageFont

# --- CRITICAL FIX FOR MOVIEPY + PILLOW 10+ COMPATIBILITY ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
# ----------------------------------------------------------

import edge_tts
from playwright.async_api import async_playwright

try:
    from moviepy.editor import (
        ColorClip,
        ImageClip,
        CompositeVideoClip,
        AudioFileClip
    )
except ImportError:
    from moviepy.video.VideoClip import ColorClip, ImageClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30

def generate_script_with_openrouter(target_url):
    """Uses OpenRouter API to construct a high-converting reel hook & voiceover script."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not api_key:
        print("[AI SCRIPT] No OPENROUTER_API_KEY found. Falling back to structured dynamic script.")
        return {
            "hook": f"Stop wasting hours on design! Check out {domain}.",
            "voiceover": f"If you want to build social media carousels in seconds, {domain} uses AI to write your copy and format high-converting slides instantly. Try it out today!"
        }

    print("[AI SCRIPT] Querying OpenRouter for viral reel script...")
    prompt = f"""
    Create a high-converting 15-second Instagram Reel / TikTok script promoting the website tool: {target_url}.
    Return strictly JSON with two keys:
    1. "hook": A short, punchy 5-8 word caption to render on screen.
    2. "voiceover": A compelling 30-40 word script for text-to-speech voiceover detailing what the tool does and its main benefit.
    Format response strictly as valid JSON with no extra commentary.
    """

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
        # Strip potential markdown formatting from LLM response
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw_text)
        print(f"[AI SCRIPT] Generated Hook: {parsed.get('hook')}")
        return parsed
    except Exception as e:
        print(f"[AI SCRIPT ERROR] {e}. Falling back to default script.")
        return {
            "hook": f"The fastest way to generate carousels!",
            "voiceover": f"Crafting engaging carousels for social media takes too long. {domain} handles design and writing automatically using AI."
        }

async def generate_voiceover(text, output_audio_path="voiceover.mp3"):
    """Generates audio voiceover using edge-tts and verifies file existence."""
    print(f"[TTS] Synthesizing speech: '{text}'...")
    communicate = edge_tts.Communicate(text, voice="en-US-ChristopherNeural")
    await communicate.save(output_audio_path)
    
    if not os.path.exists(output_audio_path) or os.path.getsize(output_audio_path) == 0:
        raise RuntimeError("[TTS ERROR] Audio file generation failed or resulted in 0 bytes!")
    
    print(f"[TTS] Voiceover successfully saved ({os.path.getsize(output_audio_path)} bytes).")
    return output_audio_path

async def capture_stealth_screenshot(url, output_img_path="webpage_capture.png"):
    """
    Scrapes the target page using Playwright with stealth configurations, 
    scrolling down slightly to capture core features.
    """
    print(f"[STEALTH SCRAPER] Navigating to {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1080, "height": 2400},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            # Smooth scroll down to expose visual features
            await page.evaluate("window.scrollBy(0, 400);")
            await asyncio.sleep(2)
            await page.screenshot(path=output_img_path, full_page=False)
            print(f"[STEALTH SCRAPER] Screenshot captured: {output_img_path}")
            return output_img_path
        except Exception as e:
            print(f"[STEALTH SCRAPER ERROR] {e}")
            return None
        finally:
            await context.close()
            await browser.close()

def create_caption_overlay(text, width=1080, height=1920, output_img_path="caption_overlay.png"):
    """Renders high-visibility subtitle overlay card."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 50)
    else:
        font = ImageFont.load_default()

    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        bbox = draw.textbbox((0, 0), line_str, font=font)
        if (bbox[2] - bbox[0]) > (width - 240):
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    wrapped_text = "\n".join(lines)
    
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=14)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) / 2
    y = height - text_h - 280  # Positioned cleanly in lower third

    padding_h = 45
    padding_v = 30
    draw.rounded_rectangle(
        [x - padding_h, y - padding_v, x + text_w + padding_h, y + text_h + padding_v],
        radius=24,
        fill=(15, 15, 15, 235),
        outline=(0, 255, 170, 255),
        width=4
    )
    
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(255, 255, 255, 255), align="center", spacing=14)
    img.save(output_img_path)
    return output_img_path

def build_and_render_reel(captured_img_path, audio_path, overlay_text, output_path="final_reel.mp4"):
    print("[ENGINE] Assembling final timeline...")
    
    audio_clip = AudioFileClip(audio_path)
    duration = max(audio_clip.duration + 0.5, 5.0)  # Ensure minimum 5-second video length
    print(f"[ENGINE] Calculated video duration: {duration:.2f} seconds.")

    clips = []

    # Layer 1: Dark background
    bg_base = ColorClip(size=(CANVAS_WIDTH, CANVAS_HEIGHT), color=(15, 15, 18), duration=duration)
    clips.append(bg_base)

    # Layer 2: Webpage Capture with dynamic panning down effect
    if captured_img_path and os.path.exists(captured_img_path):
        web_clip = ImageClip(captured_img_path).set_duration(duration)
        web_clip = web_clip.resize(width=CANVAS_WIDTH)
        
        # Animate visual panning down over the video's duration
        def scroll_effect(t):
            y_pos = -int((t / duration) * 250)
            return ('center', y_pos)
            
        web_clip = web_clip.set_position(scroll_effect)
        clips.append(web_clip)

    # Layer 3: Text Card Hook & Caption
    if overlay_text:
        caption_img = create_caption_overlay(overlay_text, CANVAS_WIDTH, CANVAS_HEIGHT)
        caption_clip = ImageClip(caption_img).set_duration(duration)
        clips.append(caption_clip)

    # Composite & Render output
    final_video = CompositeVideoClip(clips, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    final_video = final_video.set_audio(audio_clip)

    print(f"[ENGINE] Exporting video to '{output_path}' via FFMPEG...")
    final_video.write_videofile(
        output_path,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    final_video.close()
    audio_clip.close()
    print("[ENGINE] Reel generation complete!")

async def main():
    target_url = os.getenv("TOOL_URL", "[https://aicarousels.com](https://aicarousels.com)")
    
    # 1. Generate hook and voiceover script
    script_data = generate_script_with_openrouter(target_url)
    hook_text = script_data.get("hook")
    voiceover_text = script_data.get("voiceover")

    # 2. Concurrently/Sequentially generate assets
    audio_file = await generate_voiceover(voiceover_text, "voiceover.mp3")
    image_file = await capture_stealth_screenshot(target_url, "webpage_capture.png")

    # 3. Compile timeline & export
    build_and_render_reel(
        captured_img_path=image_file,
        audio_path=audio_file,
        overlay_text=hook_text,
        output_path="final_reel.mp4"
    )

if __name__ == "__main__":
    asyncio.run(main())
