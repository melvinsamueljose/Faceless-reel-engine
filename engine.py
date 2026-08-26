import os
import sys
import json
import asyncio
from PIL import Image, ImageDraw, ImageFont

# --- MOVIEPY + PILLOW 10+ COMPATIBILITY ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

import edge_tts
from playwright.async_api import async_playwright

try:
    from moviepy.editor import (
        ColorClip,
        VideoFileClip,
        ImageClip,
        CompositeVideoClip,
        AudioFileClip
    )
except ImportError:
    from moviepy.video.VideoClip import ColorClip, ImageClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30

def generate_script_with_openrouter(target_url):
    """Generates viral reel script via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not api_key:
        return {
            "hook": f"Stop making carousels manually!",
            "voiceover": f"If you need social media carousels fast, check out {domain}. Just click Create Carousel, let the AI generate your slides, and customize everything automatically!"
        }

    prompt = f"""
    Create a high-converting 10-second reel script for {target_url}.
    Return strictly JSON:
    {{
      "hook": "A short 5-7 word on-screen caption",
      "voiceover": "A crisp 25-30 word script describing the button click and live generator."
    }}
    """

    try:
        import requests
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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
        print(f"[AI SCRIPT ERROR] {e}")
        return {
            "hook": "The fastest AI Carousel Generator!",
            "voiceover": f"Watch how easy it is to create carousels with {domain}. Simply click generate and let AI build your posts!"
        }

async def generate_voiceover(text, output_audio_path="voiceover.mp3"):
    """Synthesizes voiceover speech via edge-tts."""
    print(f"[TTS] Synthesizing speech...")
    communicate = edge_tts.Communicate(text, voice="en-US-ChristopherNeural")
    await communicate.save(output_audio_path)
    return output_audio_path

async def record_interactive_session(url, record_dir="recordings", duration=10):
    """
    Launches Playwright, interacts with buttons/elements on screen, 
    and outputs a video recording file.
    """
    os.makedirs(record_dir, exist_ok=True)
    print(f"[INTERACTIVE SCRAPER] Recording interaction flow on {url}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=record_dir,
            record_video_size={"width": 1080, "height": 1920},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            # Look for common CTA buttons like 'Create Carousel', 'Get Started', 'Try for free'
            cta_selectors = [
                "a:has-text('Create Carousel')",
                "button:has-text('Create Carousel')",
                "a:has-text('Get Started')",
                "button:has-text('Get Started')",
                "a.btn",
                "button"
            ]

            clicked = False
            for selector in cta_selectors:
                if await page.locator(selector).first.is_visible():
                    print(f"[INTERACTIVE SCRAPER] Clicking CTA element: {selector}")
                    await page.locator(selector).first.click()
                    clicked = True
                    break

            if not clicked:
                print("[INTERACTIVE SCRAPER] CTA button not found, falling back to mouse scroll.")
                await page.mouse.wheel(0, 800)

            # Allow time for navigation and dynamic animation rendering
            await asyncio.sleep(duration - 3)

        except Exception as e:
            print(f"[INTERACTIVE SCRAPER ERROR] {e}")
        finally:
            await context.close()
            await browser.close()

    # Retrieve generated webm file path
    files = [os.path.join(record_dir, f) for f in os.listdir(record_dir) if f.endswith(".webm")]
    if files:
        latest_file = max(files, key=os.path.getctime)
        print(f"[INTERACTIVE SCRAPER] Successfully captured video: {latest_file}")
        return latest_file
    return None

def create_caption_overlay(text, width=1080, height=1920, output_img_path="caption_overlay.png"):
    """Generates styled subtitle card."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 48) if os.path.exists(font_path) else ImageFont.load_default()

    words = text.split()
    lines, current_line = [], []

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
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    x = (width - text_w) / 2
    y = height - text_h - 260

    draw.rounded_rectangle(
        [x - 40, y - 25, x + text_w + 40, y + text_h + 25],
        radius=20, fill=(15, 15, 15, 235), outline=(0, 255, 170, 255), width=4
    )
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(255, 255, 255, 255), align="center", spacing=14)
    img.save(output_img_path)
    return output_img_path

def build_and_render_reel(video_rec_path, audio_path, overlay_text, output_path="final_reel.mp4"):
    """Composites recorded user workflow, audio, and captions into final reel."""
    print("[ENGINE] Compositing interactive video timeline...")
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration + 0.5

    clips = [ColorClip(size=(CANVAS_WIDTH, CANVAS_HEIGHT), color=(15, 15, 18), duration=duration)]

    if video_rec_path and os.path.exists(video_rec_path):
        screen_clip = VideoFileClip(video_rec_path)
        if screen_clip.duration < duration:
            screen_clip = screen_clip.loop(duration=duration)
        else:
            screen_clip = screen_clip.subclip(0, duration)
        
        screen_clip = screen_clip.resize(height=CANVAS_HEIGHT)
        if screen_clip.w < CANVAS_WIDTH:
            screen_clip = screen_clip.resize(width=CANVAS_WIDTH)
        
        screen_clip = screen_clip.crop(
            x_center=screen_clip.w / 2, y_center=screen_clip.h / 2,
            width=CANVAS_WIDTH, height=CANVAS_HEIGHT
        )
        clips.append(screen_clip)

    if overlay_text:
        caption_img = create_caption_overlay(overlay_text, CANVAS_WIDTH, CANVAS_HEIGHT)
        clips.append(ImageClip(caption_img).set_duration(duration))

    final_video = CompositeVideoClip(clips, size=(CANVAS_WIDTH, CANVAS_HEIGHT)).set_audio(audio_clip)
    final_video.write_videofile(output_path, fps=DEFAULT_FPS, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)

    final_video.close()
    audio_clip.close()

async def main():
    target_url = os.getenv("TOOL_URL", "[https://aicarousels.com](https://aicarousels.com)")
    
    script_data = generate_script_with_openrouter(target_url)
    hook_text = script_data.get("hook")
    voiceover_text = script_data.get("voiceover")

    # Save script verification data to text file for Telegram delivery
    with open("script_summary.json", "w") as f:
        json.dump({"hook": hook_text, "voiceover": voiceover_text}, f, indent=2)

    audio_file = await generate_voiceover(voiceover_text, "voiceover.mp3")
    rec_video = await record_interactive_session(target_url, duration=10)

    build_and_render_reel(rec_video, audio_file, hook_text, "final_reel.mp4")

if __name__ == "__main__":
    asyncio.run(main())
