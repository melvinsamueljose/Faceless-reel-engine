import os
import sys
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
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

async def generate_voiceover(text, output_audio_path="voiceover.mp3"):
    """Generates natural neural voiceover audio using edge-tts."""
    print(f"[TTS] Generating speech for: '{text}'...")
    communicate = edge_tts.Communicate(text, voice="en-US-ChristopherNeural")
    await communicate.save(output_audio_path)
    print(f"[TTS] Voiceover saved to {output_audio_path}")
    return output_audio_path

async def capture_stealth_screenshot(url, output_img_path="webpage_capture.png"):
    """
    Launches Playwright with stealth flags and custom headers to bypass 
    Cloudflare bot detection and capture full high-res viewport rendering.
    """
    print(f"[STEALTH SCRAPER] Bypassing protections for {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Patch anti-bot detection variables
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            print("[STEALTH SCRAPER] Page fully loaded.")
            await asyncio.sleep(4)  # Wait for JS animation/hydration
            await page.screenshot(path=output_img_path, full_page=False)
            print(f"[STEALTH SCRAPER] Screenshot successfully saved to {output_img_path}")
            return output_img_path
        except Exception as e:
            print(f"[STEALTH SCRAPER ERROR] {e}")
            return None
        finally:
            await context.close()
            await browser.close()

def create_caption_overlay(text, width=1080, height=1920, output_img_path="caption_overlay.png"):
    """Creates a stylized, high-contrast text card overlay using PIL."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 52)
    else:
        font = ImageFont.load_default()

    # Word wrapping algorithm
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        bbox = draw.textbbox((0, 0), line_str, font=font)
        if (bbox[2] - bbox[0]) > (width - 200):
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    wrapped_text = "\n".join(lines)
    
    # Calculate bounding box for text background card
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=15)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) / 2
    y = height - text_h - 250  # Placed at bottom third of 9:16 screen

    padding_h = 40
    padding_v = 30
    draw.rounded_rectangle(
        [x - padding_h, y - padding_v, x + text_w + padding_h, y + text_h + padding_v],
        radius=20,
        fill=(10, 10, 10, 230),
        outline=(0, 255, 170, 255),
        width=4
    )
    
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(255, 255, 255, 255), align="center", spacing=15)
    img.save(output_img_path)
    return output_img_path

def build_and_render_reel(
    captured_img_path,
    audio_path,
    overlay_text,
    output_path="final_reel.mp4"
):
    print("[ENGINE] Beginning composition...")
    clips = []
    
    # Set duration based on voiceover audio track
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration + 0.5  # Adding 0.5s padding
    print(f"[ENGINE] Reel target duration: {duration:.2f}s")

    # Layer 1: Base Dark Canvas
    bg_base = ColorClip(size=(CANVAS_WIDTH, CANVAS_HEIGHT), color=(12, 12, 12), duration=duration)
    clips.append(bg_base)

    # Layer 2: Webpage Background Viewport
    if captured_img_path and os.path.exists(captured_img_path):
        web_clip = ImageClip(captured_img_path).set_duration(duration)
        web_clip = web_clip.resize(width=CANVAS_WIDTH)
        clips.append(web_clip)

    # Layer 3: Text & Caption Card
    if overlay_text:
        caption_img = create_caption_overlay(overlay_text, CANVAS_WIDTH, CANVAS_HEIGHT)
        caption_clip = ImageClip(caption_img).set_duration(duration)
        clips.append(caption_clip)

    # Render Final Composition
    final_video = CompositeVideoClip(clips, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    final_video = final_video.set_audio(audio_clip)

    print(f"[ENGINE] Rendering reel file to {output_path}...")
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
    print("[ENGINE] Export completed successfully!")

async def main():
    target_url = os.getenv("TOOL_URL", "https://aicarousels.com")
    caption = os.getenv("OVERLAY_TEXT", f"Check out {target_url.replace('https://', '')}!")
    
    # Run async pipeline operations
    audio_file = await generate_voiceover(caption, "voiceover.mp3")
    image_file = await capture_stealth_screenshot(target_url, "webpage_capture.png")

    build_and_render_reel(
        captured_img_path=image_file,
        audio_path=audio_file,
        overlay_text=caption,
        output_path="final_reel.mp4"
    )

if __name__ == "__main__":
    asyncio.run(main())
