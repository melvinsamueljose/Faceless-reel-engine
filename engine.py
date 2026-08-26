import os
import sys
import asyncio
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

try:
    from moviepy.editor import (
        ColorClip,
        ImageClip,
        VideoFileClip,
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
DEFAULT_DURATION = 10.0

async def capture_website_screenshot(url, output_img_path="page_preview.png"):
    """
    Launches headless Chromium with CI-safe flags and captures a full vertical viewport screenshot.
    """
    print(f"[PLAYWRIGHT] Capturing target URL: {url}...")
    async with async_playwright() as p:
        # Launch flags required for GitHub Actions containerized runner
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1
        )
        page = await context.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"[PLAYWRIGHT] Response status: {response.status if response else 'No Response'}")
            await asyncio.sleep(3)  # Allow asset hydration
            await page.screenshot(path=output_img_path, full_page=False)
            print(f"[PLAYWRIGHT] Saved viewport snapshot to {output_img_path}")
            return output_img_path
        except Exception as e:
            print(f"[PLAYWRIGHT ERROR] Capture failed: {e}")
            return None
        finally:
            await context.close()
            await browser.close()

def create_text_image(text, width=1080, height=1920, output_img_path="text_overlay.png"):
    """Draws centered text overlay onto a transparent PNG layer."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 54)
    else:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) / 2
    y = (height - text_h) / 2

    padding = 24
    draw.rectangle(
        [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
        fill=(0, 0, 0, 200)
    )
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    img.save(output_img_path)
    return output_img_path

def generate_reel(
    captured_img_path=None,
    audio_path=None,
    overlay_text="",
    output_path="final_reel.mp4"
):
    print("[ENGINE] Building video sequence...")
    clips_to_composite = []
    total_duration = DEFAULT_DURATION

    # 1. Base Layer (Dark Gray fallback)
    base_bg = ColorClip(
        size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        color=(20, 20, 20),
        duration=total_duration
    )
    clips_to_composite.append(base_bg)

    # 2. Captured Snapshot Layer
    if captured_img_path and os.path.exists(captured_img_path):
        print(f"[ENGINE] Compositing webpage snapshot: {captured_img_path}")
        web_clip = ImageClip(captured_img_path).set_duration(total_duration)
        web_clip = web_clip.resize(width=CANVAS_WIDTH)
        clips_to_composite.append(web_clip)
    else:
        print("[ENGINE WARNING] Snapshot file missing. Skipping background capture layer.")

    # 3. Text Overlay Layer
    if overlay_text:
        txt_img = create_text_image(overlay_text, CANVAS_WIDTH, CANVAS_HEIGHT)
        txt_clip = ImageClip(txt_img).set_duration(total_duration)
        clips_to_composite.append(txt_clip)

    # 4. Export Video
    print("[ENGINE] Writing video stream...")
    final_video = CompositeVideoClip(clips_to_composite, size=(CANVAS_WIDTH, CANVAS_HEIGHT))

    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            final_video = final_video.set_audio(audio_clip)
        except Exception as e:
            print(f"[WARNING] Audio attaching failed: {e}")

    final_video.write_videofile(
        output_path,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )
    final_video.close()
    print("[ENGINE] Complete!")

if __name__ == "__main__":
    target_url = os.getenv("TOOL_URL", "https://aicarousels.com")
    snapshot_file = "site_snapshot.png"
    
    snapshot = asyncio.run(capture_website_screenshot(target_url, snapshot_file))
    
    txt_content = os.getenv("OVERLAY_TEXT", f"Try {target_url.replace('https://', '')}")
    aud_path = os.getenv("AUDIO_PATH", "assets/voiceover.mp3")
    out_path = os.getenv("OUTPUT_PATH", "final_reel.mp4")

    generate_reel(
        captured_img_path=snapshot,
        audio_path=aud_path if os.path.exists(aud_path) else None,
        overlay_text=txt_content,
        output_path=out_path
    )
